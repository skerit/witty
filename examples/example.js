
var
	// Symlink for document
	document = window.document,
	// HTML tag
	documentElement = document.documentElement,
	// preserve original object of History
	windowHistory = window.history || {},
	// obtain a reference to the Location object
	windowLocation = window.location,
	// Check support HTML5 History API
	api = !!windowHistory.pushState,
	// If the first event is triggered when the page loads
	// This behavior is obvious for Chrome and Safari
	initialState = api && windowHistory.state === undefined,
	initialFire = windowLocation.href,
	// Just a reference to the methods
	JSON = window.JSON || {},
	defineProp = Object.defineProperty,
	defineGetter = Object.prototype.__defineGetter__,
	defineSetter = Object.prototype.__defineSetter__,
	historyPushState = windowHistory.pushState,
	historyReplaceState = windowHistory.replaceState,
	sessionStorage = window.sessionStorage,
	hasOwnProperty = Object.prototype.hasOwnProperty,
	toString = Object.prototype.toString,
	// if we are in Internet Explorer
	msie = +(((window.eval && eval("/*@cc_on 1;@*/") && /msie (\d+)/i.exec(navigator.userAgent)) || [])[1] || 0),
	// unique ID of the library needed to run VBScript in IE
	libID = ( new Date() ).getTime(),
	// counter of created classes in VBScript
	VBInc = ( defineProp || defineGetter ) && ( !msie || msie > 8 ) ? 0 : 1,
	// If IE version 7 or lower to add iframe in DOM
	iframe = msie < 8 ? document.createElement( 'iframe' ) : False,

	// original methods text links
	_a, _r, _d,
	// prefix to names of events
	eventPrefix = "",
	// saving originals event methods
	addEvent = ( _a = "addEventListener", window[ _a ] ) || ( _a = "attachEvent", eventPrefix = "on", window[ _a ] ),
	removeEvent = ( _r = "removeEventListener", window[ _r ] ) || ( _r = "detachEvent", window[ _r ] ),
	fireEvent = ( _d = "dispatchEvent", window[ _d ] ) || ( _d = "fireEvent", window[ _d ] ),

	// scopes for event listeners
	eventsListPopState = [],
	eventsListHashChange = [],

	skipHashChange = 0,

eventsList = {
	"onpopstate": eventsListPopState,
	"popstate": eventsListPopState,
	"onhashchange": eventsListHashChange,
	"hashchange": eventsListHashChange
};


