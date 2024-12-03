from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flasgger import Swagger

import requests
import nltk

# Descarga de recursos necesarios para NLTK
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab')  # Asegúrate de descargar el recurso 'punkt_tab'

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Inicializar Swagger
swagger = Swagger(app)

# Cargar las stopwords en español
stop_words = set(stopwords.words('spanish'))

# Función para analizar el mensaje del usuario
def analizar_mensaje(mensaje):
    """
    Analiza el mensaje del usuario para extraer palabras clave relevantes.
    """
    # Tokenizar el mensaje
    palabras = word_tokenize(mensaje.lower())
    
    # Filtrar palabras clave quitando stopwords y caracteres no alfabéticos
    palabras_clave = [palabra for palabra in palabras if palabra.isalnum() and palabra not in stop_words]
    
    return palabras_clave




# Realiza la solicitud a la API y obtiene los productos
def obtener_productos():
    url = 'https://riccospyp.somee.com/api/producto/active'
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error al obtener productos: {e}")
        return []


def respuesta_producto(user_input):
    # Obtener los productos de la API
    productos = obtener_productos()

    # Analizar el mensaje del usuario para obtener palabras clave
    palabras_clave = analizar_mensaje(user_input)

    # Variable para almacenar la respuesta
    respuesta = {"status": "error", "message": "No puedo entender tu pregunta."}

    # Si hay un número en la consulta, lo consideramos como un posible precio
    precios_posibles = [int(palabra) for palabra in palabras_clave if palabra.isdigit()]

    # Responder según el rango de precios solicitado
    if len(precios_posibles) == 2:
        min_precio, max_precio = sorted(precios_posibles)
        productos_encontrados = [
            producto for producto in productos
            if min_precio <= producto['precio'] <= max_precio
        ]
        if productos_encontrados:
            respuesta = {
                "status": "success",
                "productos": [
                    {"nombre": p["nombre"], "precio": p["precio"]} for p in productos_encontrados
                ]
            }
        else:
            respuesta = {
                "status": "error",
                "message": f"No encontré productos en el rango de {min_precio}-{max_precio} soles."
            }

    # Si no se encuentra una coincidencia, se devuelven todos los productos que coincidan con palabras clave
    else:
        productos_encontrados = [
            producto for producto in productos
            if any(
                palabra in producto['nombre'].lower() or palabra in producto['descripcion'].lower()
                for palabra in palabras_clave
            )
        ]
        if productos_encontrados:
            respuesta = {
                "status": "success",
                "productos": [
                    {
                        "nombre": p["nombre"],
                        "descripcion": p["descripcion"],
                        "precio": p["precio"],
                        "disponibilidad": p["disponibilidadDescripcion"]
                    }
                    for p in productos_encontrados
                ]
            }
        else:
            respuesta = {
                "status": "error",
                "message": "No encontré productos que coincidan con tu consulta."
            }

    return respuesta




# Ruta para procesar las preguntas del usuario
@app.route('/chatbot', methods=['POST'])
def chatbot():
    """
    Procesa las preguntas del usuario y responde con información sobre productos.
    ---
    parameters:
      - in: body
        name: message
        required: true
        schema:
          type: object
          properties:
            message:
              type: string
              description: Mensaje enviado por el usuario.
              example: ¿Cuánto cuesta el Pollo a la Brasa Completo?
    responses:
      200:
        description: Respuesta generada por el chatbot.
        schema:
          type: object
          properties:
            response:
              type: string
              description: Respuesta del chatbot.
              example: El precio del pollo es 20 soles.
      400:
        description: Solicitud incorrecta.
        schema:
          type: object
          properties:
            response:
              type: string
              description: Mensaje de error.
              example: Por favor, escribe una pregunta válida.
    """
    data = request.json
    user_input = data.get('message', '')
    if not user_input:
        return jsonify({'response': "Por favor, escribe una pregunta válida."}), 400
    
    response = respuesta_producto(user_input)

    return jsonify({'response': response})


if __name__ == '__main__':
    socketio.run(app, debug=True, port=5001)

