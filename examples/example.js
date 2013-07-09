/**
 * This is a messy javascript file,
 * with statements that end with semicolon or nothing,
 * multiline strings, ...
 * Mainly used for development testing
 */

/**
 * A testing Property
 *
 * @typename Person
 * 
 * @param    {string}   firstname   The name of this person
 * @param    {number}   age         The age of this person
 *
 * @property {string}   firstname   The name of this person
 */
var Person =function(firstname, age, data) {

	this.firstname = firstname
	
}

var thisIsNotAGlobal = 10

var multi, variable, declaration = true,
    over = 'multiple', lines

function(){
	var thisIsAScopeVar = 10
	var andWontBeVisibleOutsideThisFunction = true

	var bb = function bla(){

	}
}

// These are multiple statements on one line
var stest = ';;;';var we = 'are';var declaring = 'multiple';var statements = 'on one line'

// An object
var simpleObject = {wrongly: 'placed',
	key: 'test',
	second: 'value'
};

explicit = 'test'

anotherObject = {}

multilinestring = 'this is \
a test to see\
what will happen';

var Jelle = new Person('Jelle', 25, {test: true});