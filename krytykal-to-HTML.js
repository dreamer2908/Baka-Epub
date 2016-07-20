// run me in FireBug's (inspector's) console
// Firefox might hang for a few seconds
var consolePrefix = '[krytykal-HTML] ';

// Strip the header, only keep the title
var title = document.title;
title = title.replace('|', '-');
document.head.innerHTML = '<title>' + title + '</title>';

// remove the layout, only keep the content
// the layout depends on the theme. This small branching might evolve into a giant tree in future lel.
// with krytykal, the article's contents can be either multiple sub-posts (su-posts-single-post), or just the texts and images
if (document.getElementsByClassName("su-posts-single-post").length > 0) {
	// in the first case, get entry-content and unwrap all su-posts-single-post
	console.log(consolePrefix + 'Compound article with multiple sub-posts detected.');
	document.body.innerHTML = document.getElementsByClassName("entry-content")[0].innerHTML; // also add entry-titile here?
	document.body.removeAttribute("class");

	// unwrap spoiler
	var spoilers = document.getElementsByClassName("su-spoiler");
	var spoilerCount = spoilers.length;
	for (var i = 0; i < spoilers.length; i++) {
		var innerPost = spoilers[i].getElementsByClassName("su-posts-single-post")[0];
		spoilers[i].innerHTML = innerPost.innerHTML;
		spoilers[i].className = innerPost.className;
	};
	console.log(consolePrefix + 'Unwrapped ' + spoilerCount.toString() + ' spoiler(s).')

	// unwrap sections
	// don't remove stuff not in sections as sometimes contents are outside.
	var posts = document.getElementsByClassName("su-posts-single-post");
	var postCount = 0;
	do {
		for (var i = 0; i < posts.length; i++) {
			var postTitle = posts[i].getElementsByClassName("su-post-title")[0];
			var postContent = posts[i].getElementsByClassName("su-post-content")[0];
			if (postContent) { // some empty post
				if (postTitle) { // some posts might not have title
					posts[i].innerHTML = postTitle.outerHTML + postContent.innerHTML;
				} else {
					posts[i].innerHTML = postContent.innerHTML;
				};
			} else {
				posts[i].innerHTML = "";
				console.log(consolePrefix + "Post #" + i.toString() + " contains no contents. Plz check the source.");
			};
			posts[i].outerHTML = posts[i].innerHTML;
			postCount++;
		};
		posts = document.getElementsByClassName("su-posts-single-post");
	} while (posts.length > 0); // for unknown reasons, some still stay if it runs only once
	console.log(consolePrefix + 'Unwrapped ' + postCount.toString() + ' section(s).');
}
else if (document.getElementsByClassName("entry-title").length > 0) {
		// in the second case, just get entry-title and entry-content inside <article> and you're done
		console.log(consolePrefix + 'Single article type 1 detected.');
		var articleTitle = document.getElementsByClassName("entry-title")[0];
		var articleContent = document.getElementsByClassName("entry-content")[0];
		document.body.innerHTML = articleTitle.outerHTML + articleContent.innerHTML;
		document.body.removeAttribute("class"); // or document.body.className = "";
		console.log(consolePrefix + 'Unwrapped the entry content.');
}
else if (document.getElementsByClassName("page-title").length > 0) {
		// support for https://saurimania.wordpress.com/fumetsu-v1ch1/
		console.log(consolePrefix + 'Single article type 2 detected.');
		var articleTitle = document.getElementsByClassName("page-title")[0];
		var articleContent = document.getElementsByClassName("entry clear-block")[0];
		document.body.innerHTML = articleTitle.outerHTML + articleContent.innerHTML;
		document.body.removeAttribute("class"); // or document.body.className = "";
		console.log(consolePrefix + 'Unwrapped the entry content.');
}
else if (document.getElementsByClassName("post-headline").length > 0) {
		// support for theme like Chihiro site
		console.log(consolePrefix + 'Single article type 3 detected.');
		var articleTitle = document.getElementsByClassName("post-headline")[0];
		var articleContent = document.getElementsByClassName("post-bodycopy")[0];
		document.body.innerHTML = articleTitle.innerHTML + articleContent.innerHTML;
		document.body.removeAttribute("class"); // or document.body.className = "";
		console.log(consolePrefix + 'Unwrapped the entry content.');
}

// replace thumbnails in the gallery with the respective full images
// also make the result Baka-HTML-like
var galleries = document.getElementsByClassName("gallery");
var galleryID = 0;
var galleryImageCount = 0;
for (var i = 0; i < galleries.length; i++) {
	var newGallery = document.createElement("div");
	// mark the new gallery to ease the later process
	galleryID++;
	newGallery.id = '__gallery__' + galleryID;
	var imageID = 0;
	var anchors = galleries[i].getElementsByTagName('a');
	for (var j = 0; j < anchors.length; j++) {
		var innerImages = anchors[j].getElementsByTagName("img");
		if (innerImages.length > 0) {
			imageID++;
			var newGalleryBox = document.createElement("div");
			// also mark the gallery box
			var targetID = galleryID.toString() + '_' + imageID.toString();
			newGalleryBox.id = '__gallerybox__' + targetID;
			var newImage = document.createElement("img");
			newImage.alt = "__galleryimage__"; // mark as gallery image
			newImage.src = anchors[j].getAttribute("href");
			newGalleryBox.appendChild(newImage);
			newGallery.appendChild(newGalleryBox);
		};
	};
	galleries[i].outerHTML = newGallery.outerHTML;
	galleryImageCount = galleryImageCount + imageID;
};
console.log(consolePrefix + 'Processed ' + galleryID.toString() + ' galleries with ' + galleryImageCount.toString() + ' thumbnails.')

// remove caption container and caption text. only keep the image
// just remove the caption text and unwrap the caption
var imageID = 0;
var moreImage = 0;
do {
	moreImage = 0;
	var captions = document.getElementsByClassName("wp-caption");
	for (var i = 0; i < captions.length; i++) {
		moreImage++;
		imageID++;
		var captionTexts = captions[i].getElementsByClassName("wp-caption-text");
		for (var j = 0; j < captionTexts.length; j++) {
			captionTexts[j].outerHTML = '';
		}
		captions[i].outerHTML = captions[i].innerHTML;
	};
} while (moreImage > 0); // for unknown reasons, some still stay if it runs only once
console.log(consolePrefix + 'Removed ' + imageID.toString() + ' captions from images.')

// replace thumbnails with full images
// todo: find some way to reliably detect if the target is really an image
var imageID = 0;
var moreImage = 0;
do {
	moreImage = 0;
	var anchors = document.getElementsByTagName("a");
	for (var i = 0; i < anchors.length; i++) {
		var innerImages = anchors[i].getElementsByTagName("img");
		if (innerImages.length > 0) {
			imageID++;
			moreImage++;
			// kill next/previous buttons in saurimania
			var imgSrc = innerImages[0].src;
			var targetHref = anchors[i].getAttribute("href");
			if (imgSrc.indexOf('dzvfevi.png') >= 0 || imgSrc.indexOf('DzvfeVi.png') >= 0 || imgSrc.indexOf('keYGZ2w.png') >= 0 || imgSrc.indexOf('keygz2w.png') >= 0) {
				anchors[i].outerHTML = "";
			} else {
				var newImage = document.createElement("img");
				newImage.alt = "__thumbnail__" + imageID.toString();
				newImage.src = targetHref;
				anchors[i].outerHTML = newImage.outerHTML;
			}
		}
	};
} while (moreImage > 0); // for unknown reasons, some thumbnails still stay if it runs only once
console.log(consolePrefix + 'Processed ' + imageID.toString() + ' thumbnails.')

// Un-resize wordpress-hosted image
// <img class="alignnone size-full wp-image-515" src="https://saurimania.files.wordpress.com/2016/02/dkbwc8a.jpg?w=604" alt="dkbwc8a">
var imageID = 0;
var images = document.getElementsByTagName("img");
for (var i = 0; i < images.length; i++) {
	var imgSrc = images[i].src;
	if (imgSrc.indexOf('files.wordpress.com') >= 0 && imgSrc.indexOf('?') >= 0) {
		imageID++;
		var quesPos = imgSrc.indexOf('?');
		images[i].src = imgSrc.substring(0, quesPos);
	}
};
console.log(consolePrefix + 'Un-resize ' + imageID.toString() + ' wordpress-hosted images.')

// unwrap <p><span style="font-weight:400;">blablah</span></p> into <p>blablah</p>
var moreSpan = 0;
do {
	moreImage = 0;
	var spanNode = document.querySelectorAll('span');
	for (var i = 0; i < spanNode.length; i++) {
		spanStyle = spanNode[i].getAttribute("style");
		if (spanStyle && spanStyle == "font-weight:400;") {
			spanNode[i].outerHTML = spanNode[i].innerHTML;
			console.log(spanStyle);
		}
	}
} while (moreSpan > 0); // for unknown reasons, some still stay if it runs only once

// remove "share this", "like this" garbage
var garbage = document.querySelectorAll('div.sharedaddy,div.wp-post-navigation,div.jp-relatedposts');
for (var i = 0; i < garbage.length; i++) {
	garbage[i].outerHTML = '';
};

// You're done?
// erase class attribute from some specific tags. they're no longer useful. don't touch style
var elems = document.querySelectorAll('h1,h2,span,p');
for (var i = 0; i < elems.length; i++) {
	elems[i].removeAttribute("class");
};

// delete no-longer-useful variables?
// myVar = undefined;
// delete myVar;