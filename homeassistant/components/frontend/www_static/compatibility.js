!function(){"use strict";function e(e,t){if(void 0===e||null===e)throw new TypeError("Cannot convert first argument to object");for(var r=Object(e),n=1;n<arguments.length;n++){var o=arguments[n];if(void 0!==o&&null!==o)for(var i=Object.keys(Object(o)),l=0,c=i.length;l<c;l++){var a=i[l],b=Object.getOwnPropertyDescriptor(o,a);void 0!==b&&b.enumerable&&(r[a]=o[a])}}return r}({assign:e,polyfill:function(){Object.assign||Object.defineProperty(Object,"assign",{enumerable:!1,configurable:!0,writable:!0,value:e})}}).polyfill()}();
