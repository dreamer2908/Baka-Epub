# Baka-Epub

1. [Introduction](#baka-epub)
2. [Requirements](#requirements)
3. [How to use](#how-to-use)
    1. [[Advanced] Creating ePub from non-existent page](#nonexistent)
4. [Acknowledgment](#acknowledgment)

Baka-Epub is a tool to make ePub from light novel in Baka-Tsuki. It consists of two parts:

1. Baka-HTML, a user script for converting Baka-Tsuki pages into plain HTML. During that process, unwanted page elements like the layout are removed, embedded images (both inline ones and thumbnails) are replaced with the full version.
2. Baka-Epub, a Sigil plugin for cooking the plain HTML into a proper eBook. The output will look pretty much like what the gone BTE-GEN will produce. However, there're some differences which can be either improvements or just my own preferences.

Baka-Epub is designed especially for me. So if you're not me, I recommend using [WebToEpub](https://github.com/dteviot/WebToEpub) instead.

For change logs, todo list, random notes, or whatever, see [baka_epub_dev_notes.txt](baka_epub_dev_notes.txt) (yes, plain text).

## Requirements

To run Baka-HTML, you need Firefox and Greasemonkey, latest stable version recommended. A different browser with a different user script manager might work, but only the listed softwares are supported. I can't test stuff on what I don't have or use. As of 2016-07-04, I use Firefox Nightly 50.0a1 and Greasemonkey 3.8 on Linux Mint 17.3 64-bit.

To run Baka-Epub, you need Sigil version 0.8.9 or later, latest stable version (0.9.6) recommended. The plugin makes use of the Python 3.4 interpreter, `sigil_bs4` and `sigil_gumbo` packages, which are included in Sigil 0.8.9+ by default. The plugin is tested in Sigil 0.9.6 on Linux Mint 17.3 64-bit and Sigil 0.9.5 portable on Windows 7 32-bit.

## How to use

- Browse to a Baka-Tsuki webpage that contains the full text of the wanted light novel, like [Ultimate_Antihero:Volume_3](https://www.baka-tsuki.org/project/index.php?title=Ultimate_Antihero:Volume_3).
- Click on the button "Baka-Epub" in the upper right tab bar. Note: the button only appears if you install the user script properly. [Screenshot](https://i.imgur.com/SJBSV6U.png).
- The whole page will be converted to plain text. Unwanted elements will be removed. Small images will be replaced with their full version. It can take a while depending on your network connection speed and Baka-Tsuki server's state. [Screenshot](https://i.imgur.com/a7wNdmI.png).
- Save the page in Web Page, complete format (html with images, or whatever your browser calls). I recommend adding date and script version to filename, like `Ultimate Antihero - Volume 03 [2016.07.04][bke_v0.6.4].html`.  [Screenshot](https://i.imgur.com/EDx7F3u.png).
- Run Sigil. Right click on `Text` (on the left panel), and then `Add Existing Files...`. Choose the file you saved in the previous step, i.e `Ultimate Antihero - Volume 03 [2016.07.04][bke_v0.6.4].html`.
- Right click on the newly-added file, select `Rename...` and name it `Body.xhtml`.
- Now, let's select a cover image. See the list of images in `Images` section. If the cover image is already there, like `Ultimate_Antihero_03_Cover.jpg`, rename it to either `Cover.jpg` or `Cover.png`. If it's not yet there, right click on `Images` and use `Add Existing Files...` to add one, and then rename it.
- Click menu `Plugins` > `Edit` > `Baka-Epub`. The plugin will now run. You should see `Status: success` and a load of text below. [Screenshot](https://i.imgur.com/nKCgiNw.png). Note: again, Baka-Epub only appears there if you install the plugin properly.
- Now, let's generate a ToC. Click menu `Tools` > `Table Of Contents` > `Generate Table Of Contents...`. Preview the list of ToC entries there, and then click `OK`. [Screenshot](https://i.imgur.com/XlhrDc5.png).
- If you want, add/edit some information (metadata) in menu `Tools` > `Metadata Editor...`. 
- Save the result and enjoy. Again, I recommend putting script version in filename, like `Ultimate Antihero - Volume 03 [2016.07.04][bke_v0.6.4+1.0.6].epub`. Yes, the version numbers of the two parts are independant. [Screenshot](https://i.imgur.com/ofTuVnv.png).
- Feel free to validate the result with EpubCheck, the official validation tool by the organization creating ePub format. I have tested Baka-Epub with more than 30 volumes of light novel, and the chance that the output gets zero error and zero warning is nearly 100%.

### [Advanced] Creating ePub from non-existent page <a name="nonexistent"></a>

Yes, you're reading it right. This is the unique and fun ability of Baka-Epub that WebToEpub and BTE-GEN don't have.

It's actually nothing surreal. To do this, you simple pretend to create or edit a page (register an account on Baka-Tsuki and your user page is a good choice), and run the userscript on the preview panel. With this, you can get whatever you want without messing up existing stuff in Baka-Tsuki.

For example, the full text page for Monogatari Series - Volume 14 - Koyomimonogatari doesn't exist. I edit my user page with this wikitext [here](http://pastebin.com/msS0fqBF), and then do like [this](https://i.imgur.com/gCSYoJM.png), [this](https://i.imgur.com/LMrNeLY.png), and [this](https://i.imgur.com/Prwvnno.png).

## Acknowledgment

- The user script is based on the script `Baka Tsuki eBook converter` version 2 by Poligrafowicz. It was posted in JCafe24, which is down for now. Only God knows when the site will be up again.
- The CSS stylesheets `page_styles.css` and `stylesheet.css` are from BTE-GEN by Lord-Simon. The website is down, but the source code can still be access in his [Github repository](https://github.com/Lord-Simon/BTE-GEN). I don't know PHP so it doesn't matter to me.
