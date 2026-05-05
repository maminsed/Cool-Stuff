import pyautogui
from pyautogui import ImageNotFoundException
import time
import pytesseract
import winsound

MoveDuration=0.5
EMAIL="susybakur@yahoo.com"
SUBJECT="Im gonna touch you!"
CONTENT="Ohhhh.... \n whos feeling fantastic?!! bark bark :lick lick"

def locate_until_true(img_path:str):
    res = None
    while True:
        try:
            res = pyautogui.locateOnScreen(img_path,confidence=0.8,grayscale=True)
            break
        except ImageNotFoundException: 
            pass
        winsound.Beep(500,500)
        time.sleep(0.5)
    winsound.Beep(100,500)
    return res

def openChrome():
    pyautogui.press("win")
    pyautogui.typewrite("Chrome")
    locate_until_true("./images/chrome_app.png")
    pyautogui.press("enter")

    # pyautogui.click()
    time.sleep(0.1)
    #new tab
    new_tab_loc = locate_until_true("./images/chrome_plus.png")
    # pyautogui.moveTo(new_tab_loc.left + 2,new_tab_loc.top + 2,MoveDuration)
    # pyautogui.click()
    # time.sleep(0.1)
    #go to gmail
    pyautogui.typewrite('mail.google.com')
    pyautogui.press('enter')
    
    #click comopse and wait for email_interface
    time.sleep(0.5)
    composeLoc = locate_until_true("./images/compose.png")
    pyautogui.moveTo(composeLoc.left + 10,composeLoc.top + 10,MoveDuration)
    pyautogui.click()
    email_interaface = locate_until_true("./images/email_interface.png")
    
    # writing the email
    pyautogui.typewrite(EMAIL)
    pyautogui.press("enter")
    pyautogui.press("tab")
    pyautogui.typewrite(SUBJECT)
    pyautogui.press("tab")
    pyautogui.typewrite(CONTENT)
    send_location = pyautogui.locateOnScreen("./images/send.png",confidence=0.9)
    pyautogui.moveTo(send_location.left+50,send_location.top+50,MoveDuration)
    pyautogui.click()
    
if __name__ == "__main__":
    openChrome()
    # while True:
    #     print(pyautogui.position())
