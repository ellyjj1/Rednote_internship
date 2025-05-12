import os
from loguru import logger
from apis.pc_apis import XHS_Apis
from xhs_utils.common_utils import init
from xhs_utils.data_util import handle_note_info, download_note, save_to_xlsx
from email.message import EmailMessage
import smtplib
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

class Data_Spider():
    def __init__(self):
        self.xhs_apis = XHS_Apis()

    def spider_note(self, note_url: str, cookies_str: str, proxies=None):
        note_info = None
        try:
            success, msg, note_info = self.xhs_apis.get_note_info(note_url, cookies_str, proxies)
            if success:
                note_info = note_info['data']['items'][0]
                note_info['url'] = note_url
                note_info = handle_note_info(note_info)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'\u722c\u53d6\u7b14\u8bb0\u4fe1\u606f {note_url}: {success}, msg: {msg}')
        return success, msg, note_info

    def spider_some_note(self, notes: list, cookies_str: str, base_path: dict, save_choice: str, excel_name: str = '', proxies=None):
        if (save_choice == 'all' or save_choice == 'excel') and excel_name == '':
            raise ValueError('excel_name \u4e0d\u80fd\u4e3a\u7a7a')
        note_list = []
        for note_url in notes:
            success, msg, note_info = self.spider_note(note_url, cookies_str, proxies)
            if note_info is not None and success:
                note_list.append(note_info)
        for note_info in note_list:
            if save_choice == 'all' or save_choice == 'media':
                download_note(note_info, base_path['media'])
        if save_choice == 'all' or save_choice == 'excel':
            file_path = os.path.abspath(os.path.join(base_path['excel'], f'{excel_name}.xlsx'))
            save_to_xlsx(note_list, file_path)

    def spider_user_all_note(self, user_url: str, cookies_str: str, base_path: dict, save_choice: str, excel_name: str = '', proxies=None):
        note_list = []
        try:
            success, msg, all_note_info = self.xhs_apis.get_user_all_notes(user_url, cookies_str, proxies)
            if success:
                logger.info(f'\u7528\u6237 {user_url} \u4f5c\u54c1\u6570\u91cf: {len(all_note_info)}')
                for simple_note_info in all_note_info:
                    note_url = f"https://www.xiaohongshu.com/explore/{simple_note_info['note_id']}?xsec_token={simple_note_info['xsec_token']}"
                    note_list.append(note_url)
            if save_choice == 'all' or save_choice == 'excel':
                excel_name = user_url.split('/')[-1].split('?')[0]
            self.spider_some_note(note_list, cookies_str, base_path, save_choice, excel_name, proxies)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'\u722c\u53d6\u7528\u6237\u6240\u6709\u89c6\u9891 {user_url}: {success}, msg: {msg}')
        return note_list, success, msg

    def spider_some_search_note(self, query: str, require_num: int, cookies_str: str, base_path: dict, save_choice: str, sort="general", note_type=0,  excel_name: str = '', proxies=None):
        note_list = []
        try:
            success, msg, notes = self.xhs_apis.search_some_note(query, require_num, cookies_str, sort, note_type, proxies)
            if success:
                notes = list(filter(lambda x: x['model_type'] == "note", notes))
                logger.info(f'\u641c\u7d22\u5173\u952e\u8bcd {query} \u7b14\u8bb0\u6570\u91cf: {len(notes)}')
                for note in notes:
                    note_url = f"https://www.xiaohongshu.com/explore/{note['id']}?xsec_token={note['xsec_token']}"
                    note_list.append(note_url)
            if save_choice == 'all' or save_choice == 'excel':
                if not excel_name:
                    excel_name = query
            self.spider_some_note(note_list, cookies_str, base_path, save_choice, excel_name, proxies)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'\u641c\u7d22\u5173\u952e\u8bcd {query} \u7b14\u8bb0: {success}, msg: {msg}')
        return note_list, success, msg


def send_email_with_excel(excel_path: str):
    """Send email with Excel attachment using Gmail OAuth2"""

    from base64 import urlsafe_b64encode
    import google.auth.transport.requests
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    # Load credentials from .env
    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GMAIL_REFRESH_TOKEN"),
        client_id=os.getenv("GMAIL_CLIENT_ID"),
        client_secret=os.getenv("GMAIL_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token"
    )

    creds.refresh(Request())
    access_token = creds.token
    sender_email = "ellyjj2@gmail.com"
    receiver_email = "ellyjj2@gmail.com"

    msg = EmailMessage()
    msg["Subject"] = "Daily Rednote Report"
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.set_content("Hi,\n\nPlease find attached the latest Rednote Excel report.")

    # Attach the file
    with open(excel_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=os.path.basename(excel_path)
        )

    # Prepare AUTH string
    auth_string = f"user={sender_email}\1auth=Bearer {access_token}\1\1"
    auth_bytes = urlsafe_b64encode(auth_string.encode("utf-8"))

    import smtplib
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.docmd("AUTH", "XOAUTH2 " + auth_bytes.decode())
        server.send_message(msg)

    print("Email sent successfully via Gmail OAuth 2.0.")

if __name__ == '__main__':

    # Load environment variables (consider using python-dotenv)
    from dotenv import load_dotenv
    load_dotenv()  # Load from .env file

    # Initialize logging of xiaohongshu
    cookies_str, base_path = init()
    data_spider = Data_Spider()

    query = "新西兰 实习"
    query_num = 10
    sort = "time_descending"
    note_type = 0

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    excel_filename = f"{query}_{timestamp}"
    excel_path = os.path.join(base_path["excel"], excel_filename+".xlsx")
    print(excel_path)

    data_spider.spider_some_search_note(
        query, query_num, cookies_str, base_path,
        save_choice='all',
        excel_name=excel_filename,
        sort=sort,
        note_type=note_type
    )

    # Then send email (using same path)
    if os.path.exists(excel_path):
        send_email_with_excel(excel_path)
    else:
        logger.error(f"Excel file not found: {excel_path}")