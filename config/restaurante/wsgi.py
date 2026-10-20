from app import create_app

# Punto de entrada para Gunicorn, Uvicorn o el CLI de Flask
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
