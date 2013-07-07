
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
var Person = function(firstname, age) {

	this.firstname = firstname;

}

var thisIsNotAGlobal = 10;

var multi, variable, declaration = true,
    over = 'multiple', lines;

function(){
	var thisIsAScopeVar = 10;
	var andWontBeVisibleOutsideThisFunction = true;

	var bb = function bla(){

	}
}
