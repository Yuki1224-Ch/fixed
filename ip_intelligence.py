from session_noproxy import Session as Client

class IpIntelligence:
    def __init__(self, session: Client) -> None:
        self.session = session

    def get_accept_language(self) -> str:
        #response_text = self.session.get("https://ipgeolocation.io/", headers={"origin": "https://ipgeolocation.io", "referer": "https://ipgeolocation.io/"}).text
#
        #try:
        #    language = response_text.split(r'languages\":\"')[1].split('"')[0].split(",")[0]
        #except:
        #    raise ValueError("Failed to get proxy / IP information")
#
        #if language == "en-GB":
        #    accept_language = "en-GB,en-US;q=0.9,en;q=0.8"
        #else:
        #    accept_language = "en-US,en;q=0.9"

        return "en-US,en;q=0.9" #accept_language