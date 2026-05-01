from util import get_config, random_string
from output import Output
from json import dumps
from datetime import datetime, timedelta
from base64 import b64encode, b64decode
import json
import time

config = get_config()
DEBUG = config.get("debug", False)


def retry(func):
    def wrapper(*func_args, **func_kwargs):
        attempt = 0
        while attempt < 3:
            try:
                return func(*func_args, **func_kwargs)
            except Exception as e:
                print(f"Error occurred: {e}")
                attempt += 1
                if attempt == 3:
                    raise
    return wrapper


@retry
def change_birthdate_request(session, birthdate_payload):
    DEBUG and Output("INFO").log("Change_Birthdate_Request")
    response = session.post("https://users.roblox.com/v1/birthdate", json=birthdate_payload)
    if response.status_code != 200 and response.status_code != 403:
        raise Exception(f"Failed to change birthdate {response.status_code}")
    return response

@retry
def continue_challenge(session, challenge_id, token):
    DEBUG and Output("INFO").log("Change_Birthdate_Continue_Challenge")
    payload = {
        "challengeId": challenge_id,
        "challengeType": "reauthentication",
        "challengeMetadata": dumps({"reauthenticationToken": token}, separators=(",", ":"))
    }
    
    response = session.post("https://apis.roblox.com/challenge/v1/continue", json=payload)

    if response.status_code != 200:
        raise Exception(f"Reauthentication challenge continue failed {response.status_code}, {response.text}")
    return response


@retry
def change_password_request(session, new_password, old_password, sec_auth_intent):
    payload = {
        "currentPassword": old_password,
        "newPassword": new_password,
        "secureAuthenticationIntent": sec_auth_intent
    }

    response = session.post("https://auth.roblox.com/v2/user/passwords/change", json=payload)

    if response.status_code != 200 or not ".ROBLOSECURITY" in response.cookies:
        raise Exception(f"Failed to change password {response.status_code}, {response.text}")
    return True, response.cookies.get('.ROBLOSECURITY')


class Secure:
    @staticmethod
    def _get_actual_session(session_data):
        """Extract the actual session object from session data"""
        if isinstance(session_data, tuple):
            return session_data[0]  # Return the session from tuple
        return session_data  # Already a session object

    @staticmethod
    def _get_birthdate_headers(session):
        """Get headers for birthdate requests"""
        actual_session = Secure._get_actual_session(session)
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json;charset=UTF-8",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "origin": "https://www.roblox.com",
            "referer": "https://www.roblox.com/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site"
        }


        return {**actual_session.headers, **headers}

    @staticmethod
    def _handle_chef_challenge(session, challenge_info, account_password):
        DEBUG and Output("INFO").log("Handling Chef Challenge")
        
        actual_session = Secure._get_actual_session(session)
        
        cid = challenge_info["id"]
        meta = challenge_info["metadata"]
        uid = meta.get("userId")
        browserTrackerId = meta.get("browserTrackerId")
        expected_symbols = meta.get("expectedSymbols", [])
        
        URL_SUBMIT = "https://apis.roblox.com/rotating-client-service/v1/submit"
        URL_CONTINUE = "https://apis.roblox.com/challenge/v1/continue"
        
        submit_headers = {
            **actual_session.headers,
            "accept": "*/*",
            "content-type": "application/json-patch+json"
        }
        
        for val in expected_symbols:
            payload = {"userId": uid, "challengeId": cid, "payload": val}
            response = actual_session.post(URL_SUBMIT, json=payload, headers=submit_headers)

            
            if response.status_code != 200:
                return False, None
        
        cont_payload = {
            "challengeID": cid,
            "challengeMetadata": json.dumps({"userId": uid, "challengeId": cid, "browserTrackerId": browserTrackerId}),
            "challengeType": "chef",
        }

        continue_headers = {
            **actual_session.headers,
            "accept": "*/*",
            "content-type": "application/json"
        }
        
        response = actual_session.post(URL_CONTINUE, json=cont_payload, headers=continue_headers)
        
        success = response.status_code == 200
        result = response.json() if success else None
        return success, result

    @staticmethod
    def _handle_2sv_challenge(session, challenge_info, account_password):
        DEBUG and Output("INFO").log("Handling 2SV Challenge")
        
        actual_session = Secure._get_actual_session(session)
        
        cid = challenge_info["id"]
        meta = challenge_info["metadata"]
        inner_id = meta.get("challengeId")
        action = meta.get("actionType", "Generic")
        remember = meta.get("rememberDevice", False)
        uid = meta.get("userId")
        
        URL_2SV_VERIFY_BASE = "https://twostepverification.roblox.com/v1/users/{userId}/challenges/password/verify"
        URL_CONTINUE = "https://apis.roblox.com/challenge/v1/continue"
        
        url = URL_2SV_VERIFY_BASE.format(userId=uid)
        payload = {
            "challengeId": inner_id,
            "actionType": action,
            "code": account_password
        }
        
        verify_headers = {
            **actual_session.headers,
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json;charset=UTF-8"
        }
        
        response = actual_session.post(url, json=payload, headers=verify_headers)
        
        if response.status_code != 200:
            return False, None
        
        token = response.json().get("verificationToken")
        if not token:
            return False, None
        
        cont_payload = {
            "challengeID": cid,
            "challengeType": "twostepverification",
            "challengeMetadata": json.dumps({
                "verificationToken": token,
                "rememberDevice": remember,
                "challengeId": inner_id,
                "actionType": action,
            }),
        }
        
        continue_headers = {
            **actual_session.headers,
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json;charset=UTF-8"
        }
        
        response = actual_session.post(URL_CONTINUE, json=cont_payload, headers=continue_headers)
        
        success = response.status_code == 200
        challenge_state = {
            "verification_token": token,
            "inner_2sv_challenge_id": inner_id,
            "action_type": action,
            "remember_device": remember
        } if success else None
        
        return success, challenge_state

    @staticmethod
    def _process_challenge(session, response, account_password):
        DEBUG and Output("INFO").log("Processing Challenge")
        
        if response.status_code != 403 or "rblx-challenge-id" not in response.headers:
            return False, None
        
        initial_challenge_id = response.headers["rblx-challenge-id"]
        initial_challenge_type = response.headers["rblx-challenge-type"]
        
        challenge_metadata = b64decode(response.headers["rblx-challenge-metadata"]).decode()
        challenge_json = json.loads(challenge_metadata)
        
        challenge_info = {
            "id": initial_challenge_id,
            "type": initial_challenge_type,
            "metadata": challenge_json,
        }
        
        challenge_state = {
            "initial_challenge_id": initial_challenge_id,
            "initial_challenge_type": initial_challenge_type
        }
        
        success = False
        next_challenge = None
        
        if initial_challenge_type == "chef":
            success, next_challenge = Secure._handle_chef_challenge(session, challenge_info, account_password)
        elif initial_challenge_type == "twostepverification":
            success, state = Secure._handle_2sv_challenge(session, challenge_info, account_password)
            if success and state:
                challenge_state.update(state)
        else:
            return False, None
        
        if not success:
            return False, None
        
        if next_challenge and next_challenge.get("challengeType") == "twostepverification":
            metadata_str = next_challenge["challengeMetadata"]
            if metadata_str.strip().startswith("{"):
                parsed_metadata = json.loads(metadata_str)
            else:
                decoded_metadata = b64decode(metadata_str).decode()
                parsed_metadata = json.loads(decoded_metadata)
            
            success, state = Secure._handle_2sv_challenge(session, {
                "id": next_challenge["challengeId"],
                "metadata": parsed_metadata
            }, account_password)
            
            if not success or not state:
                return False, None
            
            challenge_state.update(state)
        
        return True, challenge_state

    @staticmethod
    def _make_final_birthdate_request(session, birthdate_payload, challenge_state):
        DEBUG and Output("INFO").log("Making Final Birthdate Request")
        
        actual_session = Secure._get_actual_session(session)
        
        meta_final = json.dumps({
            "verificationToken": challenge_state["verification_token"],
            "rememberDevice": challenge_state["remember_device"],
            "challengeId": challenge_state["inner_2sv_challenge_id"],
            "actionType": challenge_state["action_type"],
        })
        
        headers_final = Secure._get_birthdate_headers(session)
        headers_final.update({
            "rblx-challenge-id": challenge_state["initial_challenge_id"],
            "rblx-challenge-metadata": b64encode(meta_final.encode()).decode(),
            "rblx-challenge-type": challenge_state["initial_challenge_type"],
            "x-retry-attempt": "1",
        })
        
        response = actual_session.post(
            "https://users.roblox.com/v1/birthdate",
            json=birthdate_payload,
            headers=headers_final
        )
        
        return response.status_code == 200

    @staticmethod
    def change_birthdate(session_data, account):
        DEBUG and Output("INFO").log("Change_Birthdate")
        try:
            actual_session = Secure._get_actual_session(session_data)
            
            today = datetime.today()
            tomorrow = today + timedelta(days=4)
            adjusted_date = tomorrow.replace(year=tomorrow.year - 13)

            birthdate_payload = {
                "birthDay": adjusted_date.day,
                "birthMonth": adjusted_date.month,
                "birthYear": adjusted_date.year
            }
            headers = Secure._get_birthdate_headers(session_data)
            
            response = actual_session.post(
                "https://users.roblox.com/v1/birthdate",
                json=birthdate_payload,
                headers=headers
            )

            
            if response.status_code == 200:
                return True

            if response.status_code == 403:
                success, challenge_state = Secure._process_challenge(session_data, response, account[1])
                
                if success and challenge_state:
                    return Secure._make_final_birthdate_request(session_data, birthdate_payload, challenge_state)
                else:
                    return False
            else:
                return False

        except Exception as e:
            print(f"Error in change_birthdate: {e}")
            return False
    
    @staticmethod
    def change_password(session_data, new_password, old_password, sec_auth_intent):
        DEBUG and Output("INFO").log("Change_Password")
        actual_session = Secure._get_actual_session(session_data)
        return change_password_request(actual_session, new_password, old_password, sec_auth_intent)