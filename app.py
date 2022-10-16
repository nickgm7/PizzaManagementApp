from crypt import methods
from hashlib import new
from unicodedata import name
from flask import Flask, render_template, request, redirect, url_for, flash
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

app = Flask(__name__)
app.secret_key = "Secret Key"

#setup firestore connection
cred = credentials.Certificate("./serviceAccount.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

#A Pizza consitst of a name, toppings dict for the data, and toppings string for display
class Pizza(object):
    def __init__(self, name, toppings, toppingDisplay):
        self.name = name
        self.toppings = toppings
        self.toppingDisplay = toppingDisplay
    #get set representation of a pizza for displaying in /chef table
    @staticmethod
    def from_dict(source):
        keys = source.keys()
        return set(keys)

    def to_dict(toppings):
        t_dict = {}
        for t in toppings:
            t_dict[t] = ""
        return t_dict

    def __repr__(self):
        return (
            f'Pizza(name={self.name}, toppings={self.toppings}, toppingDisplay={self.toppingDisplay})'
        )
    def printToppings(self):
        for t in self.toppings:
            print(t)




#Check if topping exists. Returns true if exists, false if not.
def checkForTopping(topping):
    doc_ref = db.collection(u'toppings').document(topping)
    doc = doc_ref.get()
    if doc.exists:
        print(f'Document data: {doc.to_dict()}')
        return True
    else:
        print(u'No such document!')
        return False

#Check if pizza exists. Returns true if exists, false if not.
def checkForPizzas(pizza, toppings):
    #check both pizza name and toppings selection are not taken
    name_check = False
    topping_check = False
    
    #check for pizza with matching name
    doc_ref = db.collection(u'pizzas').document(pizza)
    doc = doc_ref.get()
    if doc.exists:
        name_check = True

    #check for pizza with matching toppings
    allPizzas = db.collection(u'pizzas').stream()
    for pizza in allPizzas:
        if Pizza.from_dict(pizza.to_dict()) == set(toppings):
                topping_check = True
    
    #if there is no pizza with given name and no pizza that uses given toppings return false else true
    return name_check or topping_check

#Check if pizza name exists
def checkForPizzaName(pizza):
    doc_ref = db.collection(u'pizzas').document(pizza)
    doc = doc_ref.get()
    if doc.exists:
        return True
    return False

#Check if pizza topping combo exists
def checkForPizzaToppings(toppings):
#check for pizza with matching toppings
    allPizzas = db.collection(u'pizzas').stream()
    for pizza in allPizzas:
        if Pizza.from_dict(pizza.to_dict()) == set(toppings):
                return True
    return False

#Store owner tableview
@app.route("/",  methods = ['GET', 'POST'])
def Index():
    toppingArray = []
    allToppings = db.collection(u'toppings').stream()
    for topping in allToppings:
        toppingArray.append(u'{}'.format(topping.id))

    return render_template("index.html", toppings = toppingArray)


#Add a topping
@app.route("/addTopping", methods = ['POST'])
def addTopping():

    if request.method == 'POST':
        #add new topping using input from form
        topping = request.form['topping']
        #convert to lowercase
        topping = str(topping).lower()
        #first check if topping exists before adding
        if checkForTopping(topping):
            flash("Topping already exists!", "danger")
        else:
            db.collection(u'toppings').document(topping).set({'topping' : topping})
            flash("Topping added.", "success")
            
    return redirect(url_for('Index'))

#Update topping
@app.route("/update", methods = ['GET', 'POST'])
def updateTopping():
    if request.method == 'POST':
        #edit topping using input from form
        newTopping = request.form['updateTopping']
        #used hidden form field to pass id of topping to be changed
        oldTopping = request.form['oldTopping']
        #convert to lowercase
        newTopping = str(newTopping).lower()
        #first check if topping exists before updating
        if checkForTopping(newTopping):
            flash("Topping already exists!", "danger")
        else:
            #cant change id of document so instead delete old document and create new with updated topping name
            #this will suffice as there will only be one value for toppings 
            db.collection(u'toppings').document(oldTopping).delete()
            db.collection(u'toppings').document(newTopping).set({'topping' : newTopping})
            flash("Topping updated.", "success")

    return redirect(url_for('Index'))

#delete topping
@app.route("/delete/<topping>/", methods = ['GET', 'POST'])
def deleteTopping(topping):
    db.collection(u'toppings').document(topping).delete()
    flash(f"{topping} deleted.", "success")
    return redirect(url_for('Index'))


#get string representation of a pizza for displaying in /chef table
def getToppingsString(pizza):
    pizzaStr = "("
    #get list of toppings from pizza and create a string for the tableview
    toppings = pizza.to_dict()
    for topping in toppings.keys():
        pizzaStr += topping + ", "
    
    pizzaStr = pizzaStr.rstrip(", ") 
    pizzaStr += ")"
    if pizzaStr == "()":
        return "No Toppings"
    return pizzaStr


#Chef tableview
@app.route("/chefs", methods = ['GET', 'POST'])
def chefs():
    toppingArray = []
    allToppings = db.collection(u'toppings').stream()
    for topping in allToppings:
        toppingArray.append(u'{}'.format(topping.id))


    allPizzas = db.collection(u'pizzas').stream()
    pizzas = []
    for pizza in allPizzas:
        #create pizza object from db
        p = Pizza(pizza.id, Pizza.from_dict(pizza.to_dict()), getToppingsString(pizza))
        #append to pizza objects array
        pizzas.append(p)
        
    return render_template("chefs.html", p = pizzas, t = toppingArray)

#Add a pizza
@app.route("/addPizza", methods = ['POST'])
def addPizza():
    if request.method == 'POST':
        #add new pizza using input from form
        pizza = request.form['pizza']
        toppings = request.form.getlist('toppings')
        #first check if pizza exists before adding
        if checkForPizzaName(pizza) or checkForPizzaToppings(toppings):
            flash("Pizza already exists! Please check that name and toppings combination are unique.", "danger")
        else:
            db.collection(u'pizzas').document(pizza).set(Pizza.to_dict(toppings))
            flash("Pizza added.", "success")
            
    return redirect(url_for('chefs'))

#Update pizza name
@app.route("/chefs/updatePizzaName/", methods = ['GET', 'POST'])
def updatePizzaName():
    if request.method == 'POST':
        #edit pizza using input from form
        newPizza = request.form['updatePizza']
        oldPizza = request.form['oldPizza']
        #first check if pizza exists before updating
        if checkForPizzaName(newPizza):
            flash("Pizza already exists! Please check that the name is unique.", "danger")
        else:
            #cant change id of document so instead delete old document and create new with updated topping name
            #this will suffice as there will only be one value for toppings 
            toppings = db.collection(u'pizzas').document(oldPizza).get().to_dict()
            print(toppings)
            db.collection(u'pizzas').document(oldPizza).delete()
            db.collection(u'pizzas').document(newPizza).set(toppings)
            flash("Pizza updated.", "success")
            
    return redirect(url_for('chefs'))

#Update pizza toppings
@app.route("/chefs/updatePizzaToppings/", methods = ['GET', 'POST'])
def updatePizzaToppings():
    if request.method == 'POST':
        #edit pizza using input from form
        pizza = request.form['pizza']
        toppings = request.form.getlist('toppings')
        #first check if pizza toppings combo exists before updating
        if checkForPizzaToppings(toppings):
            flash("Pizza already exists! Please check that toppings combination is unique.", "danger")
        else:
            #cant change id of document so instead delete old document and create new with updated topping name
            #this will suffice as there will only be one value for toppings 
            db.collection(u'pizzas').document(pizza).set(Pizza.to_dict(toppings))
            flash("Pizza updated.", "success")
            
    return redirect(url_for('chefs'))


#Delete pizza
@app.route("/chefs/delete/<pizza>/", methods = ['GET', 'POST'])
def deletePizza(pizza):
    db.collection(u'pizzas').document(pizza).delete()
    flash(f"{pizza} pizza deleted.", "success")
    return redirect(url_for('chefs'))


if __name__ == "__main__":
    app.run(debug=True)