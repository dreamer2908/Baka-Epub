#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os, re, codecs, random, string
import bs4
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

plugin_name = 'Baka-Epub'
plugin_version = '1.0.6'
plugin_path = ''

text_type = str

def run(bk):
	# get python plugin path
	global plugin_path
	plugin_path = os.path.join(bk._w.plugin_dir, plugin_name)

	altReadingCount = 0
	def altReadingReplace(matchobj):
		nonlocal altReadingCount
		altReadingCount += 1
		print('Correcting alternative reading: "%s" | "%s"' % (matchobj.group(1).strip(), matchobj.group(2).strip())) # note: 1 is displayed on top of 2
		return '<span style="white-space: nowrap; position: relative;"><span style="position: absolute; font-size: .8em; top: -15px; left: 50%; white-space: nowrap; letter-spacing: normal; color: inherit; font-weight: inherit; font-style: inherit;"><span style="position: relative; left: -50%;">\1</span></span><span style="display: inline-block; color: inherit; letter-spacing: normal; font-size: 1.0em; font-weight: inherit;">\2</span></span>'.replace('\1', matchobj.group(1).strip()).replace('\2', matchobj.group(2).strip())

	# Remove the default text section. Should be a xhtml file with no real content.
	del_me_id = bk.basename_to_id('Section0001.xhtml')
	if del_me_id:
		print('Removing the default text section Section0001.xhtml.')
		bk.deletefile(del_me_id)

	# check if css files exists. Add them if not
	cssFiles = ['stylesheet.css', 'page_styles.css']
	for cssFile in cssFiles:
		if bk.id_to_href(cssFile):
			print('CSS file %s already existing. Skipped adding.' % cssFile)
		else:
			cssPath = os.path.join(plugin_path, cssFile)
			cssText = codecs.open(cssPath, 'r', 'utf-8').read()
			mediaType = 'text/css'
			baseName = cssFile
			manifestID = cssFile
			bk.addfile(manifestID, baseName, cssText, mediaType)
			print('Added CSS file %s.' % cssFile)

	# create cover page
	coverImgID = createCoverPage(bk)

	bookTitle = ''
	galleryImages = []
	for (textID, textHref) in bk.text_iter():
		if os.path.split(textHref)[1] != 'Body.xhtml': # main text file must be named Body.xhtml
			continue
		print('\nProcessing text file: %s' % textHref)

		html = bk.readfile(textID) # Read the section into html
		if not isinstance(html, text_type):	# If the section is not str then sets its type to 'utf-8'
			html = text_type(html, 'utf-8')

		plsWriteBack = False

		# unwrap heading from <h1><span id='blabl'>text</span></h1> into <h1 id='blal'>text<h1>.
		# class="mw-headline" part are all removed by ebook converter
		html = re.sub('<h(\\d)><span id="(.+?)">(.+?)</span></h(\\d)>', '<h\\1 id="\\2">\\3</h\\4>', html)

		soup = BeautifulSoup(html, "xml") # must use xml as other modes don't retain upcase attribute names, thus create invalid svg codes

		# remove lang="en" attribute from <html> tag (FlightCrew complains)
		for htmlTag in soup.find_all('html'):
			if htmlTag.get('lang') != None:
				del htmlTag['lang']
				plsWriteBack = True

		# move up headings if necessary
		headingLv = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8']
		lvToMvUp = 0
		for lv in headingLv:
			tags = soup.find_all(lv)
			# print('%s = %r' % (lv, tags))
			if len(tags) == 0:
				lvToMvUp += 1
			else:
				break
		if lvToMvUp > 0:
			print('Moving headings up %d level(s).' % lvToMvUp)
			for i in range(lvToMvUp, len(headingLv)):
				for tag in soup.find_all(headingLv[i]):
					tag.name = headingLv[i-lvToMvUp]
			plsWriteBack = True

		# correct invalid id attributes of heading. TODO: handle links to these headings
		idFixedCount = 0
		for lv in headingLv:
			for headingTag in soup.find_all(lv):
				headingID = headingTag.get('id')
				fixed = False
				if headingID != None:
					if headingID != "".join(headingID.split()):
						headingID = "".join(headingID.split())
						fixed = True
					if headingID == '':
						headingID = '_' + ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
						fixed = True
					if ':' in headingID:
						headingID = headingID.replace(':', '_').replace(' ', '')
						fixed = True
					if headingID[0].isdigit() or headingID[0] == '.':
						headingID = '_' + headingID
						fixed = True
				if fixed:
					# print(headingTag)
					# print(headingID)
					headingTag['id'] = headingID
					idFixedCount += 1
		if idFixedCount > 0:
			plsWriteBack = True
			print('Corrected %d invalid id attribute(s).' % idFixedCount)

		# strip all formatings from headings as BTE-GEN does
		headingStrippedCount = 0
		for lv in headingLv:
			for headingTag in soup.find_all(lv):
				if len(headingTag.find_all('img')) == 0:
					headingTag.string = headingTag.get_text()
					headingStrippedCount += 1
		if headingStrippedCount > 0:
			plsWriteBack = True
			print('Stripped formatings from %d headings to match BTE-GEN\'s behavior.' % headingStrippedCount)

		# Clean up blank paragraphs next to headings and images.
		blankParagraphsClean = 0
		for lv in headingLv:
			for headingTag in soup.find_all(lv):
				for paragraph in headingTag.find_next_siblings('p'):
					if paragraph.get_text().strip() == '' and len(paragraph.find_all('img')) == 0:
						paragraph.decompose()
						blankParagraphsClean += 1
					else: break
				for paragraph in headingTag.find_previous_siblings('p'):
					if paragraph.get_text().strip() == '' and len(paragraph.find_all('img')) == 0:
						paragraph.decompose()
						blankParagraphsClean += 1
					else: break
		for imgTag in soup.find_all('img'):
			if imgTag.parent.name == 'p':
				for paragraph in imgTag.parent.find_next_siblings('p'):
					if paragraph.get_text().strip() == '' and len(paragraph.find_all('img')) == 0:
						paragraph.decompose()
						blankParagraphsClean += 1
					else: break
				for paragraph in imgTag.parent.find_previous_siblings('p'):
					if paragraph.get_text().strip() == '' and len(paragraph.find_all('img')) == 0:
						paragraph.decompose()
						blankParagraphsClean += 1
					else: break
		for divTag in soup.find_all('div'):
				for paragraph in divTag.find_next_siblings('p'):
					if paragraph.get_text().strip() == '' and len(paragraph.find_all('img')) == 0:
						paragraph.decompose()
						blankParagraphsClean += 1
					else: break
				for paragraph in divTag.find_previous_siblings('p'):
					if paragraph.get_text().strip() == '' and len(paragraph.find_all('img')) == 0:
						paragraph.decompose()
						blankParagraphsClean += 1
					else: break
				if len(divTag.contents) == 0:
					divTag.decompose()
					blankParagraphsClean += 1
		if blankParagraphsClean > 0:
			plsWriteBack = True
			print('Cleaned %d blank paragraphs next to headings and images.' % blankParagraphsClean)

		# handle align attribute in p, div, span
		tagsFixedCount = 0
		for pdivspanTag in soup.find_all(['p', 'div', 'span', 'caption', 'img', 'table', 'hr'] + headingLv):
			alignAttr = pdivspanTag.get('align')
			if alignAttr != None:
				styleAttr = pdivspanTag.get('style')
				if styleAttr:
					pdivspanTag['style'] = 'text-align: %s; ' % alignAttr + styleAttr
				else:
					pdivspanTag['style'] = 'text-align: %s;' % alignAttr
				del pdivspanTag['align']
				tagsFixedCount += 1
		if tagsFixedCount > 0:
			plsWriteBack = True
			print('Converted align attribute in %d p/div/span tag(s) into css style.' % tagsFixedCount)

		# handle the long deprecated center tags
		tagsFixedCount = 0
		for centerTag in soup.find_all('center'):
			if centerTag.parent.name == 'p':
				styleAttr = centerTag.parent.get('style')
				if styleAttr:
					centerTag.parent['style'] = 'text-align: center; ' + styleAttr
				else:
					centerTag.parent['style'] = 'text-align: center;'
				centerTag.unwrap()
			else:
				centerTag.name = 'div'
				centerTag['style'] = 'text-align: center;'
			tagsFixedCount += 1
		if tagsFixedCount > 0:
			plsWriteBack = True
			print('Converted %d deprecated center tag(s) into a suitable form for ePub.' % tagsFixedCount)

		# handle the deprecated u tags
		tagsFixedCount = 0
		for uTag in soup.find_all('u'):
			uTag.name = 'span'
			uTag['style'] = 'text-decoration: underline;'
			tagsFixedCount += 1
		if tagsFixedCount > 0:
			plsWriteBack = True
			print('Converted %d deprecated u tag(s) into a suitable form for ePub.' % tagsFixedCount)

		# handle the invalid usage of <i> tags in HakoMari vol 2 may 2. This is due to a major error in the source page, but it can't be helped.
		tagsFixedCount = 0
		for iTag in soup.find_all(['i']):
			illegalChild = iTag.find_all('p')
			if len(illegalChild) > 0:
				tagsFixedCount += 1
				for child in iTag.children:
					if type(child) == bs4.element.NavigableString:
						# a lot of unwanted `<p><i> </i></p>` line will be created if you wrap everything without checking
						if str(child).strip() != '':
							wrapper = child.wrap(soup.new_tag('i'))
							wrapper.wrap(soup.new_tag('p'))
					elif child.name == 'p':
						for grandChild in child.children:
							if type(grandChild) == bs4.element.Tag:
								if grandChild.name == 'i':
									grandChild.unwrap() # remove italic from italic text
								else:
									grandChild.wrap(soup.new_tag("i"))
							else:
								grandChild.wrap(soup.new_tag("i"))
					elif child.name not in headingLv: # skip styling headings
						styleAttr = child.get('style')
						if styleAttr:
							child['style'] = 'font-style: italic; ' + styleAttr
						else:
							child['style'] = 'font-style: italic;'
				iTag.unwrap()

		if tagsFixedCount > 0:
			plsWriteBack = True
			print('Fixed %d range of invalid usage of <i> tag.' % tagsFixedCount)

		# handle the deprecated tag <s> and <strike>. Use <del> instead.
		tagsFixedCount = 0
		for strikeTag in soup.find_all(['s', 'strike']):
			strikeTag.name = 'del'
			tagsFixedCount += 1
		if tagsFixedCount > 0:
			plsWriteBack = True
			print('Converted %d deprecated <s> and <strike> tag(s) into <del> tag(s).' % tagsFixedCount)

		# apply that certain customization to Baka-Tsuki's alternative reading style
		altReadingCustomized = 0
		for spanTag in soup.find_all('span'):
			styleAttr = spanTag.get('style')
			if (styleAttr and (styleAttr.replace(' ', '').startswith("position: absolute; font-size: .8em; top: -11px;".replace(' ', '')))):
				spanTag['style'] = styleAttr.replace('-11px', '-15px')
				altReadingCustomized += 1
		if altReadingCustomized > 0:
			plsWriteBack = True
			print('Customized Baka-Tsuki\'s style in %d alternative reading(s).' % altReadingCustomized)

		# fix the invalid css code in the "Status: Incomplete" message
		invalidCssCodeFixed = 0
		for divTag in soup.find_all('div'):
			styleAttr = divTag.get('style')
			if (styleAttr and ('{{#ifeq: yes | yes | margin:auto;' in styleAttr)):
				divTag['style'] = styleAttr.replace('{{#ifeq: yes | yes | margin:auto;', '/*! {{#ifeq: yes | yes | margin:auto; */')
				invalidCssCodeFixed += 1
		if invalidCssCodeFixed > 0:
			plsWriteBack = True
			print('Removed invalid CSS code in %d "Status: Incomplete" message(s).' % invalidCssCodeFixed)

		# remove the navigator at the end. How to detect: the last table, containing all baka-tsuki.org links. An automatic and simple navigator should contain only a single table. A customized navigator might contain several nested tables. Kill the biggest one together with everything inside.
		allTables = soup.find_all('table')
		if len(allTables) > 0:
			tableTag = allTables[-1]
			if tableTag:
				for tmpTag in tableTag.parents: # reach the highest level of table
					if tmpTag is not None and tmpTag.name == 'table':
						tableTag = tmpTag
				# print(tableTag)
				allATag = tableTag.find_all('a')
				if len(allATag) > 0: # table with no link doesn't count
					allBtLink = True
					for aTag in allATag:
						href = aTag.get('href')
						# print(href)
						if (href is not None) and ('baka-tsuki.org' not in href) and (not href.startswith('javascript:')): # href can be js link to collapse/expand
							allBtLink = False
				else:
					allBtLink = False
				if allBtLink:
					print('Removed the unwanted navigator (table of links to main page and other volumes) at the end of main text.')
					tableTag.decompose()

		# search for gallery images first
		for imgTag in soup.find_all('img'):
			imgSrc = imgTag.get('src')
			imgAlt = imgTag.get('alt')
			imgName = os.path.split(imgSrc)[1]

			if imgAlt.startswith('__galleryimage__'):
				# print('Found gallery image: %s' % imgName)
				imgInGallery = [ _[0] for _ in galleryImages ]
				if imgSrc not in imgInGallery:
					galleryImages.append((imgSrc, imgAlt))
				# still remove it from the text even if it's a duplicate
				outerTag = imgTag.parent
				imgTag.decompose()
				if len(outerTag.contents) == 0:
					outerTag.decompose()
		if len(galleryImages) > 0:
			plsWriteBack = True
			print('Found %d gallery images: %r.' % (len(galleryImages), [ _[0] for _ in galleryImages ]))
			plsRemoveEverythingAboveGallery = True
			for divTag in soup.find_all('div'): # eliminate gallary div and everything before it
				divID = divTag.get('id') # note that there can be multiple galleries
				if divID != None and divID.startswith('__gallery__'):
					if plsRemoveEverythingAboveGallery:
						aboveTheGallery = divTag.find_previous_siblings()
						if (len(aboveTheGallery) < 6):
							for tmpTag in aboveTheGallery:
								tmpTag.decompose()
							print('Cleaned stuff above gallery #%s.' % divID)
						else:
							print('Too much stuff above gallery #%s. Not gonna clean. Contents even before the gallery?' % divID)
					divTag.decompose()

		# wrapping img in svg
		imgWrappedInSvg = 0
		outOfGalleryImages = []
		print('Processing images in body text...')
		for imgTag in soup.find_all('img'):
			imgSrc = imgTag.get('src')
			imgName = os.path.split(imgSrc)[1]

			# remove the img from gallery if it's used in the body
			for tmp in galleryImages:
				tmpsrc, tmpalt = tmp
				if tmpsrc == imgSrc:
					outOfGalleryImages.append(tmp)
					galleryImages.remove(tmp)

			if imgTag.parent.name in headingLv:
				print('Skipped processing heading image: %s' % imgName)
				continue

			print('Processing image: %s' % imgName)

			if imgSrc.startswith('../'): imgSrc = imgSrc[3:]
			imgID = bk.href_to_id(imgSrc)

			if imgID: # image file exists
				svgNode = BeautifulSoup(getSvgForImage(bk, imgID), "xml")
				# Deal with anchor wrapping around the original img tag
				# usually <p><a href="http://somewhere.com"><img src='blabla.jpg' alt='nothing' /></a></p>
				# copy <a> to inside <div>, outside <img> or <svg>. put svgNode outside <a> (and <p> if any)
				# if <a> contains nothing but the image, kill the original <a>
				if imgTag.parent.name == 'a':
					anchorTag = imgTag.parent
					targetHref = anchorTag.get('href')
					if targetHref:
						newATag = soup.new_tag('a')
						newATag['href'] = targetHref
						for tmpTag in svgNode.find_all(['svg', 'img']):
							tmpTag.wrap(newATag)
					imgTag.parent.insert_before(imgTag)
					if len(anchorTag.contents) == 0 or (len(anchorTag.contents) == 1 and str(anchorTag.contents[0]).strip() == ''):
						anchorTag.decompose()

				# if the parent tag is p, insert svgNode before p and delete img. svg is not allowed inside p or span.
				if imgTag.parent.name == 'p':
					imgTag.parent.insert_before(svgNode)
					outerTag = imgTag.parent
					imgTag.decompose()
					if len(outerTag.contents) == 0:
						outerTag.decompose()
				elif imgTag.parent.name == 'div' or imgTag.parent.name == 'body':
					imgTag.replace_with(svgNode)
				# sometimes img tag is wrapped inside more tag than one p, like b in Heavy Object V11C3P12
				# climb the tree until a usable place is found: directly under <body> or <div>, have <div> or <p> or <a> as siblings.
				# Insert svgNode before it. Decompose the branch if it's worthless
				else:
					topBranch = imgTag
					while not (topBranch.parent.name in ['div', 'body'] or len(topBranch.find_next_siblings(['div', 'p', 'a']) + topBranch.find_previous_siblings(['div', 'p'])) > 0):
						topBranch = topBranch.parent
					topBranch.insert_before(svgNode)
					outerTag = imgTag.parent
					imgTag.decompose()
					if len(outerTag.contents) == 0:
						outerTag.decompose()

				imgWrappedInSvg += 1
			else:
				print('Error: image file not found.')
		if imgWrappedInSvg > 0:
			plsWriteBack = True
			print('Wrapped %d images in SVG.' % imgWrappedInSvg)
		if len(outOfGalleryImages) > 0:
			plsWriteBack = True
			print('Removed %d images from the gallery because they\'re used in the body text: %r' % (len(outOfGalleryImages), [ _[0] for _ in outOfGalleryImages ]))

		# re-add attributes removed by BeautifulSoup for no reason
		errorsByBsCorrected = 0
		for svgTag in soup.find_all('svg'):
			if 'xmlns' not in svgTag or 'xmlns:xlink' not in svgTag:
				errorsByBsCorrected += 1
				svgTag['xmlns'] = "http://www.w3.org/2000/svg"
				svgTag['xmlns:xlink'] = "http://www.w3.org/1999/xlink"
				for imageTag in svgTag.find_all('image'):
					try:
						imageTag['xlink:href'] = imageTag['href']
						del imageTag['href']
					except:
						pass
		if errorsByBsCorrected > 0:
			plsWriteBack = True
			print('Corrected %d errors introduced by BeautifulSoup in svg/image tag.' % errorsByBsCorrected)

		# re-clean empty div tags
		for divTag in soup.find_all('div'):
			if len(divTag.contents) == 0:
				divTag.decompose()

		# remove trash in head
		for styleTag in soup.head.find_all('style'):
			if (styleTag.get('type') == 'text/css'):
				print('Removing css style in head.')
				styleTag.decompose()
				plsWriteBack = True
		for metaTag in soup.head.find_all('meta'):
			if (metaTag.get('charset') != None):
				print('Removing meta charset in head.')
				metaTag.decompose()
				plsWriteBack = True

		# link stylesheets
		cssList = ['../Styles/page_styles.css', '../Styles/stylesheet.css']
		for linkTag in soup.head.find_all('link'):
			if (linkTag.get('rel') == 'stylesheet'):
				href = linkTag.get('href')
				if (href in cssList):
					cssList.remove(href)
					print('Stylesheet %s already linked.' % href)
		for css in cssList:
			cssLinkTag = soup.new_tag('link', href=css, rel="stylesheet", type="text/css")
			soup.head.append(cssLinkTag)
			print('Linked stylesheet %s.' % css)
			plsWriteBack = True

		# generate xhtml text. Bs creates a lot of junk xml headers, so it's better to handle the header manually
		# html = '<?xml version="1.0" encoding="utf-8"?>' + soup.prettify().replace('<?xml version="1.0" encoding="utf-8"?>', '')
		# Sigil's prettifying function tends to add needless spaces in the midle of text - tag border
		# if the html has been already prettified by BeautifulSoup
		# It's better to not prettify it here
		html = str(soup)
		html = '<?xml version="1.0" encoding="utf-8"?>' + re.sub('<\?xml\s.*?\?>', '', html)

		# handle alternative readings which have been stripped by the ebook convert script
		html = re.sub('<span>\s*?<span>\s*?<span>(.*?)</span>\s*?</span>\s*?<span>(.*?)</span>\s*?</span>', altReadingReplace, html, flags=re.DOTALL)
		if altReadingCount > 0:
			print('Corrected %d alternative readings.' % altReadingCount)
			plsWriteBack = True

		# write back if it is modified
		if plsWriteBack:
			bk.writefile(textID, html)
		else:
			print('Nothing changed.')

		bookTitle = soup.title.string.strip()

	# find and remove cover image from gallery. It might have a different name
	if coverImgID:
		coverimgfile = bk.readfile(coverImgID)
		for tmp in galleryImages:
			tmpSrc, tmpAlt = tmp
			if tmpSrc.startswith('../'):
				tmpSrc = tmpSrc[3:]
			tmpID = bk.href_to_id(tmpSrc)
			if tmpID:
				if tmpID == coverImgID:
					print('Image file %s is already used as cover image. Removing from the gallery.' % tmpSrc)
					galleryImages.remove(tmp)
				else:
					tmpFile = bk.readfile(tmpID)
					if tmpFile == coverimgfile:
						print('Image file %s is identical to cover image, byte-to-byte wise. Removing from the gallery.' % tmpSrc)
						galleryImages.remove(tmp)

	# generate gallery Illustrations.xhtml
	galleryImgID = createGalleryPage(bk, galleryImages)

	# add title and language
	if bookTitle:
		print('Setting metadata: title: %s, language: en.' % bookTitle)
		metadataxml = bk.getmetadataxml().replace('<dc:title>[No data]</dc:title>','').replace('</metadata>', '<dc:title>%s</dc:title><dc:language>en</dc:language></metadata>' % bookTitle)
		bk.setmetadataxml(metadataxml)

	print('Done.')
	return 0

def createGalleryPage(bk, galleryImages):
	if len(galleryImages) > 0:
		print('Creating illustration gallery...')

		illustrationsXHTML = '''<?xml version="1.0" encoding="utf-8" standalone="no"?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd"><html xmlns="http://www.w3.org/1999/xhtml"><head><title></title><link href="../Styles/stylesheet.css" rel="stylesheet" type="text/css" /><link href="../Styles/page_styles.css" rel="stylesheet" type="text/css" /></head><body>'''

		for tmp in galleryImages:
			tmpSrc, tmpAlt = tmp
			if tmpSrc.startswith('../'): tmpSrc = tmpSrc[3:]
			tmpID = bk.href_to_id(tmpSrc)
			if tmpID:
				illustrationsXHTML += '\n' + getSvgForImage(bk, tmpID)
			else:
				print('Error: image file %s not found.' % tmpSrc)
				continue
		illustrationsXHTML += '</body></html>'

		manifestID = 'Illustrations.xhtml'
		baseName = manifestID
		mediaType = "application/xhtml+xml"
		bk.addfile(manifestID, baseName, illustrationsXHTML, mediaType)

		spine = bk.getspine()
		newSpineEntry = (manifestID, "yes")
		if len(spine) > 0 and spine[0][0] == 'Cover.xhtml':
			spine.insert(1, newSpineEntry)
		else:
			spine.insert(0, newSpineEntry)
		bk.setspine(spine)

		print('Added gallery %s with %d images: %r.' % (manifestID, len(galleryImages), [ _[0] for _ in galleryImages ]))

		return manifestID

def createCoverPage(bk):
	if not bk.basename_to_id('Cover.xhtml'):
		coverImgs = ['Cover.jpg', 'Cover.png', 'Cover.gif']
		for coverImg in coverImgs:
			coverImgID = bk.basename_to_id(coverImg)
			if coverImgID:
				print('Found cover image %s. Creating cover page.' % coverImg)

				coverText = '''<?xml version="1.0" encoding="utf-8" standalone="no"?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"  "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd"><html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en"><head><meta content="true" name="calibre:cover" /><title>Cover</title><style type="text/css">@page {padding: 0pt; margin:0pt}body { text-align: center; padding:0pt; margin: 0pt; }</style></head><body>''' + getSvgForImage(bk, coverImgID, 100) + '''</body></html>'''

				manifestID = 'Cover.xhtml'
				baseName = manifestID
				mediaType = "application/xhtml+xml"
				bk.addfile(manifestID, baseName, coverText, mediaType)

				# set metadata/guide/spine for cover
				spine = bk.getspine()
				newSpineEntries = [(manifestID, "yes")]
				bk.setspine(newSpineEntries + spine)
				# bk.spine_insert_before(0, manifestID, "yes")
				new_guide = [("cover", "Cover", "Text/Cover.xhtml")]
				bk.setguide(new_guide)
				metadataxml = bk.getmetadataxml().replace('</metadata>', '<meta content="%s" name="cover" /></metadata>' % coverImg)
				bk.setmetadataxml(metadataxml)

				return coverImgID

def getSvgForImage(bk, manifestID, svgSizePercent=98):
	from PIL import Image
	from io import BytesIO

	if not manifestID:
		return ''
	href = bk.id_to_href(manifestID)

	if manifestID and href: # id is specified and confirmed to exist
		imgName = os.path.split(href)[1]

		imgfile = bk.readfile(manifestID)
		imgfile_obj = BytesIO(imgfile)

		try:
			im =  Image.open(imgfile_obj)
			width, height = im.size

			template = '<div class="svg_outer svg_inner"><svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" width="%d%%" height="%d%%" viewBox="0 0 __width__ __height__" preserveAspectRatio="xMidYMid meet"><image width="__width__" height="__height__" xlink:href="__addr__"/></svg></div>' % (svgSizePercent, svgSizePercent)
			if width > height: # do not wrap landscape images. They actually look better this way
				template = '<div class="svg_outer svg_inner"><img alt="" src="__addr__" width="100%" /></div>'
			imageCode = template.replace('__addr__', '../Images/' + imgName).replace('__width__', str(width)).replace('__height__', str(height))
		except Exception as e:
			print('Error occured when reading image file: ' + str(e))
			template = '<div class="svg_outer svg_inner"><img alt="" src="__addr__" /></div>'
			imageCode = template.replace('__addr__', '../Images/' + imgName)

		return imageCode
	else:
		return ''

def main():
	print ("I reached main when I should not have.\n")
	return -1

if __name__ == "__main__":
	sys.exit(main())
