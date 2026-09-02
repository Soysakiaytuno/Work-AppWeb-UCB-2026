from flask import Flask, render_template

app  = Flask(__name__)

lista = ["si", "soy", "xd"]

@app.route("/")
def index():
    return render_template("layout.html", dato='<h1>xd</h1>', datos=lista)

@app.route("/proyectos")
def proyectos():
    return render_template('proyecto/proyectos.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)