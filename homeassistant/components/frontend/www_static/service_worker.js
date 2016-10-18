"use strict";function setOfCachedUrls(e){return e.keys().then(function(e){return e.map(function(e){return e.url})}).then(function(e){return new Set(e)})}function notificationEventCallback(e,t){firePushCallback({action:t.action,data:t.notification.data,tag:t.notification.tag,type:e},t.notification.data.jwt)}function firePushCallback(e,t){delete e.data.jwt,0===Object.keys(e.data).length&&e.data.constructor===Object&&delete e.data,fetch("/api/notify.html5/callback",{method:"POST",headers:new Headers({"Content-Type":"application/json",Authorization:"Bearer "+t}),body:JSON.stringify(e)})}var precacheConfig=[["/","0a642be9e1b7fb02b86a2e52fc88a8a7"],["/frontend/panels/dev-event-550bf85345c454274a40d15b2795a002.html","6977c253b5b4da588d50b0aaa50b21f4"],["/frontend/panels/dev-info-ec613406ce7e20d93754233d55625c8a.html","8e28a4c617fd6963b45103d5e5c80617"],["/frontend/panels/dev-service-c7974458ebc33412d95497e99b785e12.html","3a551b1ea5fd8b64dee7b1a458d9ffde"],["/frontend/panels/dev-state-65e5f791cc467561719bf591f1386054.html","78158786a6597ef86c3fd6f4985cde92"],["/frontend/panels/dev-template-d23943fa0370f168714da407c90091a2.html","2cf2426a6aa4ee9c1df74926dc475bc8"],["/frontend/panels/map-49ab2d6f180f8bdea7cffaa66b8a5d3e.html","6e6c9c74e0b2424b62d4cc55b8e89be3"],["/static/core-5ed5e063d66eb252b5b288738c9c2d16.js","59dabb570c57dd421d5197009bf1d07f"],["/static/frontend-7d56d6bc46a61004c76838518ff92209.html","d986914a99641b4ce8b0d4b842ffc71f"],["/static/mdi-46a76f877ac9848899b8ed382427c16f.html","a846c4082dd5cffd88ac72cbe943e691"],["static/fonts/roboto/Roboto-Bold.ttf","d329cc8b34667f114a95422aaad1b063"],["static/fonts/roboto/Roboto-Light.ttf","7b5fb88f12bec8143f00e21bc3222124"],["static/fonts/roboto/Roboto-Medium.ttf","fe13e4170719c2fc586501e777bde143"],["static/fonts/roboto/Roboto-Regular.ttf","ac3f799d5bbaf5196fab15ab8de8431c"],["static/icons/favicon-192x192.png","419903b8422586a7e28021bbe9011175"],["static/icons/favicon.ico","04235bda7843ec2fceb1cbe2bc696cf4"],["static/images/card_media_player_bg.png","a34281d1c1835d338a642e90930e61aa"],["static/webcomponents-lite.min.js","b0f32ad3c7749c40d486603f31c9d8b1"]],cacheName="sw-precache-v2--"+(self.registration?self.registration.scope:""),ignoreUrlParametersMatching=[/^utm_/],addDirectoryIndex=function(e,t){var a=new URL(e);return"/"===a.pathname.slice(-1)&&(a.pathname+=t),a.toString()},createCacheKey=function(e,t,a,n){var c=new URL(e);return n&&c.toString().match(n)||(c.search+=(c.search?"&":"")+encodeURIComponent(t)+"="+encodeURIComponent(a)),c.toString()},isPathWhitelisted=function(e,t){if(0===e.length)return!0;var a=new URL(t).pathname;return e.some(function(e){return a.match(e)})},stripIgnoredUrlParameters=function(e,t){var a=new URL(e);return a.search=a.search.slice(1).split("&").map(function(e){return e.split("=")}).filter(function(e){return t.every(function(t){return!t.test(e[0])})}).map(function(e){return e.join("=")}).join("&"),a.toString()},hashParamName="_sw-precache",urlsToCacheKeys=new Map(precacheConfig.map(function(e){var t=e[0],a=e[1],n=new URL(t,self.location),c=createCacheKey(n,hashParamName,a,!1);return[n.toString(),c]}));self.addEventListener("install",function(e){e.waitUntil(caches.open(cacheName).then(function(e){return setOfCachedUrls(e).then(function(t){return Promise.all(Array.from(urlsToCacheKeys.values()).map(function(a){if(!t.has(a))return e.add(new Request(a,{credentials:"same-origin"}))}))})}).then(function(){return self.skipWaiting()}))}),self.addEventListener("activate",function(e){var t=new Set(urlsToCacheKeys.values());e.waitUntil(caches.open(cacheName).then(function(e){return e.keys().then(function(a){return Promise.all(a.map(function(a){if(!t.has(a.url))return e.delete(a)}))})}).then(function(){return self.clients.claim()}))}),self.addEventListener("fetch",function(e){if("GET"===e.request.method){var t,a=stripIgnoredUrlParameters(e.request.url,ignoreUrlParametersMatching);t=urlsToCacheKeys.has(a);var n="index.html";!t&&n&&(a=addDirectoryIndex(a,n),t=urlsToCacheKeys.has(a));var c="/";!t&&c&&"navigate"===e.request.mode&&isPathWhitelisted(["^((?!(static|api|local|service_worker.js|manifest.json)).)*$"],e.request.url)&&(a=new URL(c,self.location).toString(),t=urlsToCacheKeys.has(a)),t&&e.respondWith(caches.open(cacheName).then(function(e){return e.match(urlsToCacheKeys.get(a)).then(function(e){if(e)return e;throw Error("The cached response that was expected is missing.")})}).catch(function(t){return console.warn('Couldn\'t serve response for "%s" from cache: %O',e.request.url,t),fetch(e.request)}))}}),self.addEventListener("push",function(e){var t;e.data&&(t=e.data.json(),e.waitUntil(self.registration.showNotification(t.title,t).then(function(e){firePushCallback({type:"received",tag:t.tag,data:t.data},t.data.jwt)})))}),self.addEventListener("notificationclick",function(e){var t;notificationEventCallback("clicked",e),e.notification.close(),e.notification.data&&e.notification.data.url&&(t=e.notification.data.url,t&&e.waitUntil(clients.matchAll({type:"window"}).then(function(e){var a,n;for(a=0;a<e.length;a++)if(n=e[a],n.url===t&&"focus"in n)return n.focus();if(clients.openWindow)return clients.openWindow(t)})))}),self.addEventListener("notificationclose",function(e){notificationEventCallback("closed",e)});