import sys
if sys.platform.startswith("win"):
    import win32com.client as outlook
    import pythoncom
    import pywintypes
from threading import Thread


def send_email(subject='PH Subject', to='', cc='', msg='PH message', attach='C:\\Dyno_v2\\Logs\\std-9.log'):
    def action():
        pythoncom.CoInitialize()
        try:
            ol = outlook.Dispatch("outlook.application")
            olmailitem = 0x0 #size of the new email
            newmail = ol.CreateItem(olmailitem)
            newmail.Subject = subject
            newmail.Sender = 'DynoNotifications@acceleratedsystems.com'
            newmail.To = to
            newmail.CC = cc
            newmail.Body = msg
            # attach='C:\\Users\\admin\\Desktop\\Python\\Sample.xlsx'
            if isinstance(attach, list):
                for item in attach:
                    newmail.Attachments.Add(item)
            else:
                newmail.Attachments.Add(attach)
            newmail.Send()
        except pywintypes.com_error:
            pass

    Thread(target=action).start()


def test_email(to, attach):
    send_email('Test', to=to, msg='Test', attach=attach)

def over_speed_email(to, attach, cc=''):
    send_email('DYNO ALERT: OVER SPEED', to=to, cc=cc, msg='Dyno stopped due to over speed!', attach=attach)

def over_torque_email(to, attach, cc=''):
    send_email('DYNO ALERT: OVER TORQUE', to=to, cc=cc, msg='Dyno stopped due to over torque!', attach=attach)

def test_interrupted_email(to, attach, cc=''):
    send_email('DYNO ALERT: TEST INTERRUPTED', to=to, cc=cc, msg='Dyno stopped due to interrupt to test script!', attach=attach)

def end_of_script_email(to, attach, test, cc=''):
    send_email('DYNO INFO: TEST FINISHED', to=to, cc=cc, msg=f'Test {test} finished!', attach=attach)

def progress_email(to, attach, msg, cc=''):
    send_email('DYNO INFO: PROGRESS REPORT', to=to, cc=cc, msg=msg, attach=attach)
