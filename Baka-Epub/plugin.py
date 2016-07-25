#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os, re, codecs, random, string, uuid, io
import sigil_bs4
import sigil_gumbo_bs4_adapter as gumbo_bs4
from PIL import Image
from io import BytesIO

plugin_name = 'Baka-Epub'
plugin_version = '1.3.0'
plugin_path = ''

text_type = str

def run(bk):
	# get python plugin path
	global plugin_path
	plugin_path = os.path.join(bk._w.plugin_dir, plugin_name)

	# check if css files exists. Add them if not
	addStylesheetFiles(bk)

	# scan all text files, gather gallery images, get book title, extract and process main texts
	mainText, galleryImages, bookTitle = processMainText(bk)

	# create cover page
	coverText, coverImgID = getCoverText(bk)

	# find and remove cover image from gallery. It might have a different name
	removeCoverImageFromGallery(bk, coverImgID, galleryImages)

	# generate gallery Illustrations.xhtml
	galleryText = getGalleryText(bk, galleryImages)

	# set metadata: cover, title, language. get BookId
	BookId = processMetadata(bk, bookTitle, coverImgID)

	# remove all existing text files, except for the default text section
	# Sigil will crash if all existing text files are removed, even if you add some later
	textFileToKeepID = [bk.basename_to_id('Section0001.xhtml'), 'Cover.xhtml', 'Illustrations.xhtml']
	for textFileInfo in bk.text_iter():
		manifest_id, OPF_href = textFileInfo
		if manifest_id not in textFileToKeepID:
			bk.deletefile(manifest_id)

	# write text files, create spine (order of text file), guide (cover text file)
	guideElement = []
	spineElement = []

	if bk.id_to_href('Cover.xhtml', None): # write to the existing file if any
		manifestID = 'Cover.xhtml'
		if coverText:
			bk.writefile(manifestID, coverText)
		spineElement.append((manifestID, 'yes'))
	elif coverText:
		guideElement.append(("cover", "Cover", "Text/Cover.xhtml"))

		manifestID = 'Cover.xhtml'
		baseName = manifestID
		mediaType = "application/xhtml+xml"
		bk.addfile(manifestID, baseName, coverText, mediaType)

		spineElement.append((manifestID, 'yes'))

	if bk.id_to_href('Illustrations.xhtml', None): # write to the existing file if any
		manifestID = 'Illustrations.xhtml'
		if galleryText:
			bk.writefile(manifestID, galleryText)
		spineElement.append((manifestID, 'yes'))
	elif galleryText:
		manifestID = 'Illustrations.xhtml'
		baseName = manifestID
		mediaType = "application/xhtml+xml"
		bk.addfile(manifestID, baseName, galleryText, mediaType)

		spineElement.append((manifestID, 'yes'))

	for i in range(len(mainText)):
		text = mainText[i]
		if i == 0:
			manifestID = getUniqueManifestIdAndBasename(bk, 'Body.xhtml')
		else:
			manifestID = getUniqueManifestIdAndBasename(bk, 'Body%d.xhtml' % i)
		baseName = manifestID
		mediaType = "application/xhtml+xml"
		bk.addfile(manifestID, baseName, text, mediaType)

		spineElement.append((manifestID, 'yes'))

	bk.setguide(guideElement)
	bk.setspine(spineElement)

	generateToC(bk, bookTitle, BookId)

	print('Done.')
	return 0

def generateToC(bk, bookTitle, BookId):
	print('Generating Table of Contents.')

	def createNavPointTag(tocSoup, navPointID, playOrder, entryLabel, entrySrc, entryLevel):
		navPointTag = tocSoup.new_tag('navPoint')
		navPointTag['id'] = navPointID
		navPointTag['playOrder'] = playOrder

		textTag = tocSoup.new_tag('text')
		textTag.string = entryLabel

		navLabelTag = tocSoup.new_tag('navLabel')
		navLabelTag.append(textTag)

		contentTag = tocSoup.new_tag('content')
		contentTag['src'] = entrySrc

		levelTag = tocSoup.new_tag('level')
		levelTag.string = entryLevel

		navPointTag.append(navLabelTag)
		navPointTag.append(contentTag)
		navPointTag.append(levelTag)

		return navPointTag

	tocXml = '<?xml version="1.0" encoding="UTF-8"?> <!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">  <ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"> <head> <meta name="dtb:uid" content="%s"/> <meta name="dtb:depth" content="2"/> <meta name="dtb:totalPageCount" content="0"/> <meta name="dtb:maxPageNumber" content="0"/> </head> <docTitle> <text>%s</text> </docTitle> <navMap> </navMap> </ncx>' % (BookId, bookTitle)
	tocSoup = sigil_bs4.BeautifulSoup(tocXml, 'xml')
	navMap = tocSoup.find('navMap')
	navID = 0

	headingLv = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8']
	headingLvN = {'h1':1, 'h2':2, 'h3':3, 'h4':4, 'h5':5, 'h6':6, 'h7':7, 'h8':8}
	lastTocEntry = None
	for textFileInfo in bk.text_iter():
		textID, textHref = textFileInfo

		html = bk.readfile(textID) # Read the section into html
		if not isinstance(html, text_type):	# If the section is not str then sets its type to 'utf-8'
			html = text_type(html, 'utf-8')
		soup = gumbo_bs4.parse(html)

		entryInThisFile = 0
		for headingTag in soup.find_all(headingLv):
			# all heading in body text files should have been given their id.
			# If one doesn't have its id, it's not in body text, so just ignore it.
			# Don't mind text files that don't have any entry. It's not an issue (Sigil's behavior)
			if headingTag.get('id'):
				entryLabel = headingTag.get_text()
				if entryInThisFile == 0: # first entry in the file should point to the beginning of the file (Sigil's behavior)
					entrySrc = textHref
				else:
					entrySrc = textHref + '#' + headingTag.get('id')
				entryLevel = headingTag.name
				entryLevelN = headingLvN[entryLevel]

				navID += 1
				navPointID = 'navPoint-%d' % navID
				playOrder = navID
				navPointTag = createNavPointTag(tocSoup, navPointID, playOrder, entryLabel, entrySrc, entryLevel)

				if not lastTocEntry:
					# first entry
					navMap.append(navPointTag)
				else:
					# climb the tree until you find a nav of higher level, or reach navMap
					parentCandidate = lastTocEntry
					parentCandidate_levelN = headingLvN[parentCandidate.find('level').string]
					while (parentCandidate.name != 'navMap' and (entryLevelN <= parentCandidate_levelN)):
						parentCandidate = parentCandidate.parent
						try:
							parentCandidate_levelN = headingLvN[parentCandidate.find('level').string]
						except:
							parentCandidate_levelN = 0
					parentCandidate.append(navPointTag)

				lastTocEntry = navPointTag
				entryInThisFile += 1

	# if no heading found, add a Start entry to the first text file
	if navID == 0:
		for textFileInfo in bk.text_iter():
			textID, textHref = textFileInfo
			navID = 1
			navPointID = 'navPoint-%d' % navID
			playOrder = navID
			entryLabel = 'Start'
			entrySrc = textHref
			entryLevel = 'h1'
			navPointTag = createNavPointTag(tocSoup, navPointID, playOrder, entryLabel, entrySrc, entryLevel)
			navMap.append(navPointTag)
			break

	# remove all level tag. it's only useful for building the tree. it's not supposed to exist in toc
	for levelTag in navMap.find_all('level'):
		levelTag.decompose()

	# also measure toc depth
	tocDepth = 0
	for navPointTag in navMap.find_all('navPoint'):
		thisDepth = 1
		parent = navPointTag.parent
		while parent.name != 'navMap':
			thisDepth += 1
			parent = parent.parent
		if thisDepth > tocDepth:
			tocDepth = thisDepth
	# set tocdepth
	for metaTag in tocSoup.find_all('meta'):
		if metaTag.get('name') == "dtb:depth":
			metaTag['content'] = str(tocDepth)

	# print('\n\n\n\n\n')
	# print(tocSoup)
	bk.writefile(bk.gettocid(), tocSoup.prettify())

def getUniqueManifestIdAndBasename(bk, startName):
	rootname, extension = os.path.splitext(startName)
	uniqueName = startName

	if (bk.id_to_href(uniqueName, None) or bk.basename_to_id(uniqueName, None)): # basename or id exists
		n = 0
		while (bk.id_to_href(uniqueName, None) or bk.basename_to_id(uniqueName, None)):
			uniqueName = '%s_%d%s' % (rootname, n, extension)
			n += 1
	return uniqueName

def processMetadata(bk, bookTitle, coverImgID):
	# set metadata: cover, title, language. get BookId
	metadata_xml = bk.getmetadataxml()
	metadata_soup = sigil_bs4.BeautifulSoup(metadata_xml, 'xml')
	metadata_node = metadata_soup.find('metadata')

	BookId = ''
	for node in metadata_node.find_all('identifier'):
		if node.get('id') == "BookId":
			BookId = node.string
			break
	if not BookId:
		print('Creating a new BookID.')
		BookId = uuid.uuid4().urn
		id_node = metadata_soup.new_tag('dc:identifier')
		id_node['id'] = "BookId"
		id_node['opf:scheme'] = "UUID"
		id_node.string = BookId
		metadata_node.append(id_node)

	for node in metadata_node.find_all(['meta', 'title', 'language']): # remove existing info
		if not (node.name == 'meta' and node.get('name') != 'cover'):
			node.decompose()

	print('Setting metadata: title: %s, language: en.' % bookTitle)
	title_tag = metadata_soup.new_tag('dc:title')
	title_tag.string = bookTitle
	metadata_node.append(title_tag)
	lang_tag = metadata_soup.new_tag('dc:language')
	lang_tag.string = 'en'
	metadata_node.append(lang_tag)

	if coverImgID:
		meta_cover_tag = metadata_soup.new_tag('meta')
		meta_cover_tag['name'] = 'cover'
		meta_cover_tag['content'] = coverImgID
		metadata_node.append(meta_cover_tag)

	bk.setmetadataxml(str(metadata_soup))

	return BookId

def addStylesheetFiles(bk):
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

def correctDuplicateOrInvalidID(bk, soup):
	# originally for correcting multiple T/N sections with identical IDs (all starts from 1) in krytykal source
	# now it corrects ALL duplicated and invalid IDs
	# step 1: collect anchors and targets (tag having ID) with their position in the tree
	anchors = [] # tuple of (tag, position in tree)
	targets = [] # same as above
	tagPosition = 0
	for descendant in soup.body.descendants:
		tagPosition += 1
		if type(descendant) == sigil_bs4.element.Tag:
			if descendant.name == 'a':
				href = descendant.get('href')
				if href and href.startswith('#'): # external links are outside the scope of this logic
					anchors.append((descendant, tagPosition))
			if descendant.get('id') != None: # anchor can be also a target
				targets.append((descendant, tagPosition))
	# print('anchors = %r' % anchors)
	# print('targets = %r' % targets)
	# step 2: put anchors and targets into groups where id and #id match. Don't care about lonesome ones
	idGroups = {} # <id> : <list of anchors and target having that id>
	for target in targets:
		targetID = target[0].get('id')
		if targetID not in idGroups:
			idGroups[targetID] = [target]
		else:
			idGroups[targetID].append(target)
	for anchor in anchors:
		targetID = anchor[0].get('href')[1:] # remove the # at the beginning
		if targetID not in idGroups:
			idGroups[targetID] = [anchor]
		else:
			idGroups[targetID].append(anchor)
	# step 3: sort the lists by tagPosition
	# see http://stackoverflow.com/questions/3121979/how-to-sort-list-tuple-of-lists-tuples
	for listOfStuff in idGroups.values():
		listOfStuff.sort(key=lambda tup: tup[1])
	# print(idGroups['_note-1'])
	# step 4: slice lists into segments of a single target and its anchor(s). The target can be either first or last in its segment.
	# the first segment of lists can keep their id. later segments must get new ids, one for each segment
	def findSegment(myList, _id, start=0):
		if start == len(myList) - 1: # reached the end of list
			return start, start
		# if the segment starts with a target, it ends before the next target or at the end of list
		# else: it ends at the first encounting target or at the end of list
		end = len(myList) - 1
		foundTheEnd = False
		for i in range(start + 1, len(myList)):
			if myList[i][0].get('id') == _id: # anchors can have id. It's rare, but possible
				if myList[start][0].get('id') == _id:
					end = i - 1
				else:
					end = i
				break
		return start, end

	idCorrected = 0
	for _id in idGroups.keys():
		idGroup = idGroups[_id]
		keepIdAllowed = isValidId(_id)
		itemIndex = 0
		while (itemIndex < len(idGroup)):
			segStart, segEnd = findSegment(idGroup, _id, itemIndex)
			if not keepIdAllowed:
				idCorrected += 1
				newID = 'id-' + str(uuid.uuid4())
				for item in idGroup[segStart:segEnd+1]:
					if item[0].get('id') == _id:
						item[0]['id'] = newID
					elif item[0].get('href') == '#' + _id:
						item[0]['href'] = '#' + newID
			itemIndex = segEnd + 1
			keepIdAllowed = False
	return idCorrected

def isValidId(headingID):
	if (not headingID) or (headingID != "".join(headingID.split())) or (':' in headingID) or headingID[0].isdigit() or headingID[0] == '.':
		return False
	return True

def processMainText(bk):
	altReadingCount = 0
	def altReadingReplace(matchobj):
		nonlocal altReadingCount
		altReadingCount += 1
		print('Correcting alternative reading: "%s" | "%s"' % (matchobj.group(1).strip(), matchobj.group(2).strip())) # note: 1 is displayed on top of 2
		return '<span style="white-space: nowrap; position: relative;"><span style="position: absolute; font-size: .8em; top: -15px; left: 50%; white-space: nowrap; letter-spacing: normal; color: inherit; font-weight: inherit; font-style: inherit;"><span style="position: relative; left: -50%;">\1</span></span><span style="display: inline-block; color: inherit; letter-spacing: normal; font-size: 1.0em; font-weight: inherit;">\2</span></span>'.replace('\1', matchobj.group(1).strip()).replace('\2', matchobj.group(2).strip())

	bookTitle = 'Untitled'
	galleryImages = []
	mainText = []
	for (textID, textHref) in bk.text_iter():
		if os.path.split(textHref)[1] in ['Cover.xhtml', 'Section0001.xhtml', 'Illustrations.xhtml']: # main text file is anything but these
			continue
		print('\nProcessing text file: %s' % textHref)

		html = bk.readfile(textID) # Read the section into html
		if not isinstance(html, text_type):	# If the section is not str then sets its type to 'utf-8'
			html = text_type(html, 'utf-8')

		plsWriteBack = False

		# unwrap heading from <h1><span id='blabl'>text</span></h1> into <h1 id='blal'>text<h1>.
		# class="mw-headline" part are all removed by ebook converter
		html = re.sub('<h(\\d)><span id="(.+?)">(.+?)</span></h(\\d)>', '<h\\1 id="\\2">\\3</h\\4>', html)

		soup = gumbo_bs4.parse(html)

		# remove lang="en" attribute from <html> tag (FlightCrew complains)
		for htmlTag in soup.find_all('html'):
			if htmlTag.get('lang') != None:
				del htmlTag['lang']
				plsWriteBack = True

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

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

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

		# add Id to headings missing it
		idFixedCount = 0
		for headingTag in soup.find_all(headingLv):
			if not headingTag.get('id'):
				headingTag['id'] = 'id-' + str(uuid.uuid4())
				idFixedCount += 1
		if idFixedCount > 0:
			plsWriteBack = True
			print('Added ID attribute to %d heading(s).' % idFixedCount)

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

		# originally for correcting multiple T/N sections with identical IDs (all starts from 1) in krytykal source
		# now it corrects ALL duplicated and invalid IDs
		idCorrected = correctDuplicateOrInvalidID(bk, soup)
		if idCorrected > 0:
			print('Corrected %d duplicated/invalid IDs and their corresponding anchors (if any).' % idCorrected)
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

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

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

		# wrap phantom <br> tag and text in <p> (krytykal source)
		phantomWrapped = 0
		plsWriteBack = True
		for child in soup.body.contents:
			if type(child) == sigil_bs4.element.NavigableString:
				# a lot of unwanted `<p> </p>` line will be created if you wrap everything without checking
				if str(child).strip() != '':
					child.wrap(soup.new_tag('p'))
					phantomWrapped += 1
				else:
					child.replace_with('\n') # eliminate blank phantom texts that aren't newline or true white spaces
			elif type(child) == sigil_bs4.element.Tag:
				if child.name in ['br']: # put phantom tags to wrap here
					child.wrap(soup.new_tag('p'))
					phantomWrapped += 1
		if phantomWrapped > 0:
			plsWriteBack = True
			print('Wrapped %d phantom <br> tag(s) and text(s) in <p>.' % phantomWrapped)
		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

		# Clean up blank paragraphs next to headings and images.
		blankParagraphsToClean = []
		for lv in headingLv:
			for headingTag in soup.find_all(lv):
				for paragraph in headingTag.find_next_siblings('p'):
					if paragraph.get_text().strip() == '' and len(paragraph.find_all('img')) == 0:
						blankParagraphsToClean.append(paragraph)
					else: break
				for paragraph in headingTag.find_previous_siblings('p'):
					if paragraph.get_text().strip() == '' and len(paragraph.find_all('img')) == 0:
						blankParagraphsToClean.append(paragraph)
					else: break
		for imgTag in soup.find_all('img'):
			if imgTag.parent.name == 'p':
				for paragraph in imgTag.parent.find_next_siblings('p'):
					if paragraph.get_text().strip() == '' and len(paragraph.find_all('img')) == 0:
						blankParagraphsToClean.append(paragraph)
					else: break
				for paragraph in imgTag.parent.find_previous_siblings('p'):
					if paragraph.get_text().strip() == '' and len(paragraph.find_all('img')) == 0:
						blankParagraphsToClean.append(paragraph)
					else: break
		for divTag in soup.find_all('div'):
				for paragraph in divTag.find_next_siblings('p'):
					if paragraph.get_text().strip() == '' and len(paragraph.find_all('img')) == 0:
						blankParagraphsToClean.append(paragraph)
					else: break
				for paragraph in divTag.find_previous_siblings('p'):
					if paragraph.get_text().strip() == '' and len(paragraph.find_all('img')) == 0:
						blankParagraphsToClean.append(paragraph)
					else: break
				if len(divTag.contents) == 0:
					blankParagraphsToClean.append(divTag)
		for endTag in soup.body.contents[::-1]:
			if type(endTag) == sigil_bs4.element.Tag:
				if endTag.name == 'p' and endTag.get_text().strip() == '' and len(endTag.find_all('img')) == 0:
					blankParagraphsToClean.append(endTag)
				else: break
		for startTag in soup.body.contents:
			if type(startTag) == sigil_bs4.element.Tag:
				if startTag.name == 'p' and startTag.get_text().strip() == '' and len(startTag.find_all('img')) == 0:
					blankParagraphsToClean.append(startTag)
				else: break
		if len(blankParagraphsToClean) > 0:
			plsWriteBack = True
			# print(blankParagraphsToClean)
			blankParagraphsToClean = removeDuplicateBs4Object(blankParagraphsToClean)
			for paragraph in blankParagraphsToClean:
				paragraph.decompose()
			print('Cleaned %d blank paragraphs next to headings and images.' % len(blankParagraphsToClean))

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

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

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

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

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

		# handle the deprecated u tags
		tagsFixedCount = 0
		for uTag in soup.find_all('u'):
			uTag.name = 'span'
			uTag['style'] = 'text-decoration: underline;'
			tagsFixedCount += 1
		if tagsFixedCount > 0:
			plsWriteBack = True
			print('Converted %d deprecated u tag(s) into a suitable form for ePub.' % tagsFixedCount)

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

		# handle the invalid usage of <i> tags in HakoMari vol 2 may 2. This is due to a major error in the source page, but it can't be helped.
		tagsFixedCount = 0
		for iTag in soup.find_all(['i']):
			illegalChild = iTag.find_all('p')
			if len(illegalChild) > 0:
				tagsFixedCount += 1
				for child in iTag.children:
					if type(child) == sigil_bs4.element.NavigableString:
						# a lot of unwanted `<p><i> </i></p>` line will be created if you wrap everything without checking
						if str(child).strip() != '':
							wrapper = child.wrap(soup.new_tag('i'))
							wrapper.wrap(soup.new_tag('p'))
					elif child.name == 'p':
						for grandChild in child.children:
							if type(grandChild) == sigil_bs4.element.Tag:
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

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

		# handle the deprecated tag <s> and <strike>. Use <del> instead.
		tagsFixedCount = 0
		for strikeTag in soup.find_all(['s', 'strike']):
			strikeTag.name = 'del'
			tagsFixedCount += 1
		if tagsFixedCount > 0:
			plsWriteBack = True
			print('Converted %d deprecated <s> and <strike> tag(s) into <del> tag(s).' % tagsFixedCount)

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

		# correct some attributes in <a> tag (krytykal source)
		# name -> id
		# data-imagelightbox and data-rel -> hell
		tagsFixedCount = 0
		for anchorTag in soup.find_all(['a']):
			if anchorTag.has_attr('name'):
				anchorTag['id'] = anchorTag['name']
				del anchorTag['name']
				tagsFixedCount += 1
			if anchorTag.has_attr('data-imagelightbox') or anchorTag.has_attr('data-rel'):
				del anchorTag['data-imagelightbox']
				del anchorTag['data-rel']
				tagsFixedCount += 1
		if tagsFixedCount > 0:
			plsWriteBack = True
			print('Corrected %d <a> tag(s) with invalid attibute(s).' % tagsFixedCount)
		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

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

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

		# remove all "Status: Incomplete" messages
		# signatures:
		# + <div style="width:25%; border:10px solid white; clear:both; float:right; text-align:center;">
		# + <b>Status: Incomplete</b>
		# + <div style="clear:both; {{#ifeq: yes | yes | margin:auto; text-align:center;">
		removeMe = []
		for divTag in soup.find_all('div'):
			hasWidth25percent = False
			hasStatusIncompleteMsg = False
			hasFaultyCssStyle = False

			styleAttr = divTag.get('style')
			if styleAttr and ('width:25%;' in re.sub('\s', '', styleAttr)):
				hasWidth25percent = True

			bTags = divTag.find_all('b')
			subDivTags = divTag.find_all('div')
			for bTag in bTags:
				if bTag.get_text().strip() == 'Status: Incomplete':
					hasStatusIncompleteMsg = True
					break

			for subDivTag in subDivTags:
				styleAttr = subDivTag.get('style')
				if (styleAttr and ('{{#ifeq: yes | yes | margin:auto;' in styleAttr)):
					hasFaultyCssStyle = True
					break
			if hasWidth25percent and hasStatusIncompleteMsg and hasFaultyCssStyle:
				removeMe.append(divTag)

		if len(removeMe) > 0:
			plsWriteBack = True
			for garbage in removeMe:
				# print(garbage)
				garbage.decompose()
			print('Removed %d "Status: Incomplete" message(s).' % len(removeMe))

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

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

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

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

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

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

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

		# wrapping img in svg
		imgWrappedInSvg = 0
		outOfGalleryImages = []
		print('Processing images in body text...')
		for imgTag in soup.find_all('img'):
			imgSrc = imgTag.get('src')
			imgWidth = imgTag.get('width')
			imgHeight = imgTag.get('height')
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
				svgNode = gumbo_bs4.parse(getSvgForImage(bk, imgID, dispWidth=imgWidth, dispHeight=imgHeight))
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

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

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

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

		# re-clean empty div tags
		for divTag in soup.find_all('div'):
			if len(divTag.contents) == 0:
				divTag.decompose()
				plsWriteBack = True

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

		# remove trash in head
		for styleTag in soup.head.find_all('style'):
			if (styleTag.get('type') == 'text/css'):
				print('Removing css style in head.')
				styleTag.decompose()
				plsWriteBack = True

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

		for metaTag in soup.head.find_all('meta'):
			if (metaTag.get('charset') != None):
				print('Removing meta charset in head.')
				metaTag.decompose()
				plsWriteBack = True

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

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

		if plsWriteBack:
			html = soup.serialize_xhtml()
			soup = gumbo_bs4.parse(html)
			plsWriteBack = False

		# Sigil's prettifying function tends to add needless spaces in the midle of text - tag border
		# if the html has been already prettified by BeautifulSoup
		# It's better to not prettify it here
		html = soup.serialize_xhtml()

		# handle alternative readings which have been stripped by the ebook convert script
		html = re.sub('<span>\s*?<span>\s*?<span>(.*?)</span>\s*?</span>\s*?<span>(.*?)</span>\s*?</span>', altReadingReplace, html, flags=re.DOTALL)
		if altReadingCount > 0:
			print('Corrected %d alternative readings.' % altReadingCount)
			plsWriteBack = True

		mainText.append(html)

		if soup.title.string:
			bookTitle = soup.title.string.strip()

	print(' ')
	return mainText, galleryImages, bookTitle

def removeCoverImageFromGallery(bk, coverImgID, galleryImages):
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

def getGalleryText(bk, galleryImages):
	galleryImageCount = len(galleryImages)
	galleryImageList = [ _[0] for _ in galleryImages ]

	if galleryImageCount > 0:
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

		print('Created an illustration gallery with %d images: %r.' % (galleryImageCount, galleryImageList))

		return illustrationsXHTML
	else:
		print('The illustration gallery is empty. Skipped creating.')
		return ''

def getCoverText(bk):
	# get cover image id from metadata
	coverImgID = ''
	metadata = bk.getmetadataxml()
	stinx = sigil_bs4.BeautifulSoup(metadata, 'xml')
	for node in stinx.find_all('meta'):
		if node.get('name') == 'cover':
			coverImgID = node.get('content')
			break
	# fail back to searching by image name
	if not coverImgID:
		coverImgCandidates = ['Cover.jpg', 'Cover.png', 'Cover.gif']
		for candidate in coverImgCandidates:
			candidateID = bk.basename_to_id(candidate, None)
			if candidateID:
				coverImgID = candidateID

	if coverImgID:
		coverImg = bk.id_to_href(coverImgID)
		print('Found cover image %s.' % coverImg)

		coverText = '''<?xml version="1.0" encoding="utf-8" standalone="no"?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"  "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd"><html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en"><head><meta content="true" name="calibre:cover" /><title>Cover</title><style type="text/css">@page {padding: 0pt; margin:0pt}body { text-align: center; padding:0pt; margin: 0pt; }</style></head><body>''' + getSvgForImage(bk, coverImgID, 100) + '''</body></html>'''

		return coverText, coverImgID
	else:
		return '', ''

def getSvgForImage(bk, manifestID, svgSizePercent=98, dispWidth=None, dispHeight=None):
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
			if width < 400 and height < 400: # don't stretch small images
				template = '<div class="svg_outer svg_inner"><img alt="" src="__addr__" /></div>'
				# use the original display resolution if it's available and is even smaller
				# note that dispWidth and dispHeight might not be pixel
				# don't bother with something like 70%
				if isfloat(dispWidth) and isfloat(dispHeight):
					dispWidth = int(float(dispWidth))
					dispHeight = int(float(dispHeight))
					if dispWidth < width and dispHeight < height:
						template = '<div class="svg_outer svg_inner"><img alt="" src="__addr__" width="%d" height="%d" /></div>' % (dispWidth, dispHeight)
			imageCode = template.replace('__addr__', '../Images/' + imgName).replace('__width__', str(width)).replace('__height__', str(height))
		except Exception as e:
			print('Error occured when reading image file: ' + str(e))
			template = '<div class="svg_outer svg_inner"><img alt="" src="__addr__" /></div>'
			imageCode = template.replace('__addr__', '../Images/' + imgName)

		return imageCode
	else:
		return ''

def isfloat(value):
	try:
		float(value)
		return True
	except ValueError:
		return False

def removeDuplicateBs4Object(inList):
	# see https://www.crummy.com/software/BeautifulSoup/bs4/doc/#comparing-objects-for-equality
	outList = []
	for bs4Obj in inList:
		seen = False
		for existingObj in outList:
			if bs4Obj is existingObj:
				seen = True
		if not seen:
			outList.append(bs4Obj)
	return outList

def main():
	print ("I reached main when I should not have.\n")
	return -1

if __name__ == "__main__":
	sys.exit(main())
