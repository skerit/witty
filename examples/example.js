
/**
 * This is a testing function
 * 
 * @property   {String}   name   The name of this person
 *
 * @param      {String}   name   The name to give to this person
 * @param      {Number}   age    The age of this person
 */
var Person = function Person(name, age) {

	this.name = name;
	this.age = age;

	/** db1 */
	var dbtest, zever;

	/**
	 * test
	 */
	this.method = function() {
		return 0;
	}

}

var obj = {
	test: 1
}

var t = 1;

var newScope = function() {
	this.test = 1;
}