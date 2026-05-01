# auth_intent.py - FIXED & WORKING
from curl_cffi import requests
from base64 import b64encode
from time import time
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import random

class AuthIntent:
    @staticmethod
    def string_to_bytes(raw_string) -> bytes:
        return bytes(raw_string, 'utf-8')

    @staticmethod
    def export_public_key_as_spki(public_key) -> str:
        spki_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return b64encode(spki_bytes).decode('utf-8')

    @staticmethod
    def generate_signing_key_pair_unextractable() -> tuple:
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key = private_key.public_key()
        return private_key, public_key

    @staticmethod
    def sign(private_key, data) -> str:
        signature = private_key.sign(data, ec.ECDSA(hashes.SHA256()))
        return b64encode(signature).decode('utf-8')

    @staticmethod
    def get_auth_intent(session: requests.Session) -> dict | None:
        try:
            # CRITICAL HEADERS - Updated for 2025
            session.headers.update({
                "Origin": "https://www.roblox.com",
                "Referer": "https://www.roblox.com/login",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
                "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            })

            # Generate key pair
            private_key, public_key = AuthIntent.generate_signing_key_pair_unextractable()
            client_public_key = AuthIntent.export_public_key_as_spki(public_key)
            client_epoch_timestamp = str(int(time() * 1000))  # Roblox uses milliseconds

            # Get server nonce with retry logic
            url = "https://apis.roblox.com/hba-service/v1/getServerNonce"
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    resp = session.get(url, impersonate="chrome124", timeout=10)
                    
                    if resp.status_code == 200:
                        break
                    
                    # Wait before retry
                    if attempt < max_retries - 1:
                        import time as time_module
                        time_module.sleep(1.5 * (attempt + 1))
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        import time as time_module
                        time_module.sleep(1.5 * (attempt + 1))
                    continue
            
            if resp.status_code != 200:
                print(f"[DEBUG] Failed to get nonce after {max_retries} attempts (status: {resp.status_code})")
                return None

            server_nonce = resp.text.strip().strip('"')
            if not server_nonce or len(server_nonce) < 10:
                print(f"[DEBUG] Invalid server nonce received: {server_nonce[:20] if server_nonce else 'None'}...")
                return None

            # Construct payload and sign
            payload = f"{client_public_key}|{client_epoch_timestamp}|{server_nonce}"
            sai_signature = AuthIntent.sign(private_key, AuthIntent.string_to_bytes(payload))

            return {
                "clientPublicKey": client_public_key,
                "clientEpochTimestamp": client_epoch_timestamp,
                "serverNonce": server_nonce,
                "saiSignature": sai_signature
            }

        except Exception as e:
            print(f"[DEBUG] AuthIntent failed: {e}")
            import traceback
            traceback.print_exc()
            return None