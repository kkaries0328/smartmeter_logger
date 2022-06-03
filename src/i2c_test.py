import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
from time import sleep
import datetime

DEVICE_ADR = 0x3C
DISP_WIDTH = 128
DISP_HEIGHT = 64
BORDER = 5

def main():
    # setting some variables for our reset_pin etc...
    RESET_PIN = digitalio.DigitalInOut(board.D4)

    # Very Important... This lets py-gaugette "know" what pins to use in order to reset the display
    i2c = board.I2C()
    oled = adafruit_ssd1306.SSD1306_I2C(DISP_WIDTH, DISP_HEIGHT, i2c, addr=DEVICE_ADR)


    # clear display
    oled.fill(0)
    oled.show()

    # create blank image for drawing
    image = Image.new("1", (oled.width, oled.height))
    draw = ImageDraw.Draw(image)

    font = ImageFont.truetype("/usr/share/fonts/truetype/fonts-japanese-gothic.ttf", 14)

    # Draw the text
    dt_now = datetime.datetime.now()
    draw.text((0, 0), dt_now.strftime('%m/%d %H:%M'), font=font, fill=255)
    draw.text((0, 20), "消費電力: 100 W", font=font, fill=255)
    # draw.text((0, 30), "Hello!", font=font2, fill=255)
    # draw.text((34, 46), "Hello!", font=font2, fill=255)

    # Display image
    oled.image(image)
    oled.show()

    sleep(5)

    # Clear display.
    oled.fill(0)
    oled.show()

    return

if __name__ == "__main__":
    main()