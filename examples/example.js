/**
 * @type {Number}
 */
var multiline = 1,

	/**
	 * @type {Number}
	 */
    declaration = 2,

	/**
	 * @type {Number}
	 */
    are = 3,

	/**
	 * @type {Number}
	 */
    go;


go.myproperty = 1;
go.another = 1;

/**
 * @type {Number}
 */
go.another.test = 1;

/**
 * @param   {Number}   myparam   The parameter
 * @class 1
 */
function Class2 (myparam) {
	this.test = 1;

}

Class2.test = 1;
Class2.prototype.PROT = 1;


var copy = Class2;

var bt = true;

var copybt = bt;

/**
 * @type {Class2}
 */
var ctest;

