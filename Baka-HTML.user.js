// ==UserScript==
// @name        Baka-HTML
// @namespace   http://localhost
// @include     /^http[s]*?:\/\/(www\.|)baka-tsuki\.org\/project\/index\.php\?title=(.*)/
// @include     /^http[s]*?:\/\/web\.archive\.org\/web\/\d*\/http[s]*?:\/\/(www\.|)baka-tsuki\.org\/project\/index\.php\?title=(.*)/
// @version     1.2.6
// @grant       none
// ==/UserScript==

var clickMe = document.createElement("li");
clickMe.innerHTML = '<span><a href="javascript:;" id="Baka-HTML">Baka-HTML</a></span></li>';
$('#p-views ul').append(clickMe);

var consolePrefix = '[Baka-HTML] ';
var title = document.title;
var imagesToProcess = 0;
var processedImages = 0;
var imageArray = [];

function dethumbnelize(img, success)
{
	imagesToProcess++;
	document.title = "Downloading images " + processedImages + "/" + imagesToProcess;
	console.log(consolePrefix + 'Image #' + imagesToProcess);

	// normally, you will be redirected to image page (/project/index.php?title=File:Imagename.jpg) if you click on the image
	// but it's entirely possible that the image (both inline and thumb) links to somewhere else
	// the filename in src is the same as that in image page url
	// make sure you use relative path to support web.archive.org
	var imgSrc = $(img).attr('src');
	console.log(consolePrefix + 'imgSrc = ' + imgSrc);
	if (imgSrc.charAt(imgSrc.length) == '/') { imgSrc = imgSrc.substring(0, imgSrc.length); } // kill the trailing slash if any

	var colonPos = imgSrc.indexOf(':');
	var thumbPos = imgSrc.indexOf('/project/thumb.php?f=');
	var imagePos = imgSrc.indexOf('/project/images/');
	var ampPos = imgSrc.indexOf('&');
	var imgName = "";
	var imgPageURL = "";
	if (thumbPos >= 0 && ampPos >= 0) { // resized images src="/project/thumb.php?f=Utsuro_no_Hako_vol1_pic1.jpg&amp;width=1000"
		imgName = imgSrc.substring(thumbPos + '/project/thumb.php?f='.length , ampPos);
		imgPageURL = '/project/index.php?title=File:' + imgName;
	}
	else if (imagePos >= 0) { // full-size image src="/project/images/3/37/UtsuroNoHako_vol1.jpg"
		imgName = imgSrc.substring(imgSrc.lastIndexOf('/') + 1);
		imgPageURL = '/project/index.php?title=File:' + imgName;
	}
	else { // unknown. fallback to where the image point to.
		var parent = img.closest('a');
		if (parent !== null) {
			imgPageURL = parent.attr('href');
		}
	}
	console.log(consolePrefix + 'imgPageURL = ' + imgPageURL);
	if (imgPageURL.length > 0) {
		$.get(imgPageURL, function(data)
		{
			var newSrc = $(data).find('.fullImageLink > a').attr('href');
			console.log(consolePrefix + 'newSrc = ' + newSrc);
			success(newSrc);
			processedImages++;
			if (processedImages < imagesToProcess) {
				document.title = "Downloading images " + processedImages + "/" + imagesToProcess;
				if (imageArray.indexOf(newSrc) == -1) {
					imageArray.push(newSrc);
				}
			} else {
				document.title = title;
				console.log(consolePrefix + 'Processed ' + imageArray.length.toString() + ' images (duplicates excluded):');
				console.log(consolePrefix + imageArray.toString());
			}
		});
	} else { // can't find the image page url
		success(imgSrc);
		processedImages++;
		if (processedImages < imagesToProcess) {
			document.title = "Downloading images " + processedImages + "/" + imagesToProcess;
		} else {
			document.title = title;
		}
	}
}

function dethumbnelize2(img, targetID, success) {
	dethumbnelize(img, function(src) {
		success(src, targetID);
	});
}

$('#Baka-HTML').click(function(){
	// format the title a bit
	title = title.replace(':', ' - ').replace(' - Baka-Tsuki', '');
	// Pad volume number in title if existing. Note that number before the last hyphen can be a part of the title
	var hypPos = title.lastIndexOf('-');
	var titlesub = title.substring(hypPos);
	var digiPos = titlesub.search(/\d/);
	if (digiPos > 0) {
		var r = /\d+/;
		var n = titlesub.match(r);
		var digiLen = n.toString().length;
		var leadingStr = '0';
		if (titlesub.charAt(digiPos) == '0' || n >= 10) {
			leadingStr = '';
		}
		if (titlesub.charAt(digiPos-1) !== ' ') { // add a space before the number
			leadingStr = ' ' + leadingStr;
		}
		title = title.substring(0, hypPos) + titlesub.substring(0, digiPos) + leadingStr + n + titlesub.substring(digiPos + digiLen);
	}
	// remove "Editing " or "Creating " from title in preview tab mode
	if (document.URL.indexOf('&action=edit') >= 0) {
		if (title.indexOf('Editing ') >= 0) {
			title = title.substring('Editing '.length);
		} else if (title.indexOf('Creating ') >= 0) {
			title = title.substring('Creating '.length);
		}
	}
	// remove the layout, only keep the content text
	if ($('div.wikiEditor-preview-contents').length > 0) {
		console.log(consolePrefix + 'Preview tab in editing page detected.');
		document.body.innerHTML = $('.wikiEditor-preview-contents').html(); // preview in edit page
	} else if ($('#mw-content-text').length > 0) {
		console.log(consolePrefix + 'Normal page detected.');
		document.body.innerHTML = $('#mw-content-text').html(); // normal
	} else {
		console.log(consolePrefix + "Contents not detected. You're running me on the wrong page.");
		alert(consolePrefix + "Contents not detected. You're running me on the wrong page.");
	}
	// remove a lot of needless page elements
	// .cite-accessibility-label is the "Jump Up" text that pops out of nowhere in notes when saving page
	// .wikitable.collapsible is big navigator at the end
	// .toc and .toctoggle are table of contents at the beginning. Yes, you need to remove both
	$('#navbar, #top, #jump-to-nav, #mw-js-message, #catlinks, .toc, .toctoggle, .printfooter, .mw-editsection, .wikitable.collapsible, .cite-accessibility-label').remove();
	// replace thumbnails in the gallery with the respective full images. Side note: traditional? Then what is the modern one?
	// each thumbnail is like this
	// <li class="gallerybox" style="width: 155px"><div style="width: 155px">
	// 		<div class="thumb" style="width: 150px;"><div style="margin:15px auto;"><a href="/project/index.php?title=File:Ultimate_Antihero_V1_cover.jpg" class="image"><img alt="" src="/project/thumb.php?f=Ultimate_Antihero_V1_cover.jpg&amp;width=85" width="85" height="120" data-file-width="1354" data-file-height="1898" /></a></div></div>
	//  	<div class="gallerytext"><p><b>Cover</b></p></div>
	// </div></li>
	// there can be multiple galleries
	var galleryID = 0;
	$('.gallery.mw-gallery-traditional').each(function()
	{
		var oldGallery = $(this);
		var newGallery = document.createElement("div");
		// mark the new gallery to ease the later process
		galleryID++;
		newGallery.id = '__gallery__' + galleryID;
		// put full images to the new gallery
		var imageID = 0;
		oldGallery.find('.gallerybox').each(function()
		{
			var self = $(this);
			imageID++;
			var newGalleryBox = document.createElement("div");
			// mark the gallery box with an id to maintain image order. The 'dethumbnelize' process is asynchoronous,
			// so without this, the order can be wrong. In fact, the chance it's wrong is more than 50/50.
			var targetID = galleryID.toString() + '_' + imageID.toString();
			newGalleryBox.id = '__gallerybox__' + targetID;
			newGallery.appendChild(newGalleryBox);
			// sometimes the image doesn't exist, so gallery box has no images
			// example https://baka-tsuki.org/project/index.php?title=Toaru_Majutsu_no_Index:NT_Volume16
			if (self.find('img').length > 0) {
				dethumbnelize2(self.find('img'), targetID, function(src, tgtID)
				{
					var newGalleryBoxImage = document.createElement("img");
					newGalleryBoxImage.src = src;
					newGalleryBoxImage.alt = '__galleryimage__'; // mark as gallery image
					$('#__gallerybox__' + tgtID).append(newGalleryBoxImage);
					console.log(consolePrefix + 'Inserted image to __gallerybox__' + tgtID);
				});
			} else {
				console.log(consolePrefix + 'This gallery box has no image. Skipping.')
				imageID--;
			}
		});
		// Replace old gallery with the new one
		oldGallery.replaceWith(newGallery);
	});
	// do the same with illustration thumbnails.
	// <div class="thumb tright"><div class="thumbinner" style="width:302px;"><a href="/project/index.php?title=File:Ultimate_Antihero_V1_c11.png" class="image"><img alt="Ultimate Antihero V1 c11.png" src="/project/thumb.php?f=Ultimate_Antihero_V1_c11.png&amp;width=300" width="300" height="423" class="thumbimage" srcset="/project/thumb.php?f=Ultimate_Antihero_V1_c11.png&amp;width=450 1.5x, /project/thumb.php?f=Ultimate_Antihero_V1_c11.png&amp;width=600 2x" data-file-width="1346" data-file-height="1898" /></a>  <div class="thumbcaption"><div class="magnify"><a href="/project/index.php?title=File:Ultimate_Antihero_V1_c11.png" class="internal" title="Enlarge"></a></div></div></div></div>
	$('div.thumb').each(function()
	{
		var self = $(this);
		var illustrationParagraph = document.createElement("p");
		var illustration = document.createElement("img");
		dethumbnelize(self.find('img'), function(src)
		{
			illustration.src = src;
			illustration.alt = '__thumbnail__';
			illustrationParagraph.appendChild(illustration);
			self.replaceWith(illustrationParagraph);
		});
	});
	// Process inline image like this one https://www.baka-tsuki.org/project/index.php?title=Utsuro_no_Hako:Volume1_1st_time
	// Pls also kill the anchor, if any
	// <a href="/project/index.php?title=File:Utsuro_no_Hako_vol1_pic1.jpg" class="image"><img alt="Utsuro no Hako vol1 pic1.jpg" src="/project/thumb.php?f=Utsuro_no_Hako_vol1_pic1.jpg&amp;width=1000" width="1000" height="731" srcset="/project/images/4/4f/Utsuro_no_Hako_vol1_pic1.jpg 1.5x, /project/images/4/4f/Utsuro_no_Hako_vol1_pic1.jpg 2x" data-file-width="1368" data-file-height="1000" /></a>
	// <a href="/project/index.php?title=File:UtsuroNoHako_vol1.jpg" class="image"><img alt="UtsuroNoHako vol1.jpg" src="/project/images/3/37/UtsuroNoHako_vol1.jpg" width="1050" height="1500" data-file-width="1050" data-file-height="1500" /></a>
	// <a href="/project/index.php?title=Ultimate_Antihero:Volume_4" title="Ultimate Antihero:Volume 4"><img alt="UnlimitedFafnir v11 008&amp;clean.jpg" src="/project/thumb.php?f=UnlimitedFafnir_v11_008%26clean.jpg&amp;width=200" width="200" height="282" srcset="/project/thumb.php?f=UnlimitedFafnir_v11_008%26clean.jpg&amp;width=300 1.5x, /project/thumb.php?f=UnlimitedFafnir_v11_008%26clean.jpg&amp;width=400 2x" data-file-width="1453" data-file-height="2048" /></a>
	$('img').each(function()
	{
		var self = $(this);
		var imgSrc = self.attr('src');
		var imgAlt = self.attr('alt');
		var thumbPos = imgSrc.indexOf('/project/thumb.php?f=');
		var imagePos = imgSrc.indexOf('/project/images/');
		var ampPos = imgSrc.indexOf('&');
		var parent = self.closest('a');
		if ((imgAlt !== '__thumbnail__' && imgAlt !== '__galleryimage__') && ((thumbPos >= 0 && ampPos >= 0) || (thumbPos == -1 && imagePos >= 0))) {
			dethumbnelize(self, function(src)
			{
				var illustration = document.createElement("img");
				illustration.src = src;
				illustration.alt = src;
				if (parent !== null) {
					parent.replaceWith(illustration);
				} else {
					self.replaceWith(illustration);
				}
			});
		}
	});
	// erase all class info. it's no longer useful, except in table. Do not erase style.
	$('*').not('table').removeAttr("class");
	// Only keep the title in the header. Note: When saving the html, the browser might add some css junk. That can be handled later.
	document.head.innerHTML = '<title>' + title + '</title>';
	// remove contextmenu attribute from body
	document.body.removeAttribute("contextmenu");
});