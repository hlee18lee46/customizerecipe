from flask import Flask, jsonify, render_template, request, render_template_string, redirect, url_for, send_from_directory
import os
import base64
import requests
import json  # Import json for pretty printing
import openai

app = Flask(__name__)

# OpenAI API Key
api_key = ""
#replace with your key


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

# Function to encode the image
@app.route("/upload")
def upload():
    # Basic form for file upload
    return """
    <form method="post" action="/analyze" enctype="multipart/form-data">
        <input type="file" name="image">
        <input type="submit">
    </form>
    """

@app.route("/hello")
def hello_world():
    # This is the new endpoint that returns "Hello World"
    return "Hello, World!"


@app.route("/analyze", methods=["POST"])
def analyze_image():
    if 'image' not in request.files:
        print("debug11")
    file = request.files['image']
    if file.filename == '':
        return 'No selected file'
    if file:
        base64_image = base64.b64encode(file.read()).decode('utf-8')

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        prompt = "Can you return a list of ingredients in the fridge as JSON object as follows: {{'fridge_contents': [{{item:}}]}}?"
        formatted_prompt = prompt.format() 
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": formatted_prompt,
                        },
                        {
                            "type": "image",
                            "image_url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    ],
                }
            ],
            "max_tokens": 300,
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
        )
        response_data = response.json()

        # Extract the ingredients text from the response
        if (
            response_data
            and "choices" in response_data
            and len(response_data["choices"]) > 0
        ):
            content_text = response_data["choices"][0]["message"]["content"]
            # Extract the JSON string from the content
            json_start = content_text.find("{")
            json_end = content_text.rfind("}") + 1
            ingredients_json = content_text[json_start:json_end]

            # Save the JSON string to a file
            try:
                with open('ingredients.json', 'w') as json_file:
                    json_file.write(ingredients_json)
                return redirect(url_for('recipe'))
                #return jsonify({"message": "JSON saved successfully"}), 200
            except IOError:
                return jsonify({"error": "Failed to save JSON"}), 500
        else:
            return jsonify({"error": "Unable to extract ingredients"}), 500
        
@app.route('/ingredients.json')
def serve_ingredients():
    directory = os.path.join(app.root_path)  # Path to the directory where ingredients.json is located
    return send_from_directory(directory, 'ingredients.json')

@app.route('/recipe')
def recipe():
    try:
        with open('ingredients.json', 'r') as json_file:
            ingredients_data = json.load(json_file)
    except FileNotFoundError:
        ingredients_data = {"error": "File not found"}
    except json.JSONDecodeError:
        ingredients_data = {"error": "Error decoding JSON"}

    # Pass the loaded data to the recipe.html template
    return render_template('recipe.html', data=ingredients_data)
@app.route('/recipes.json')
def recipe_json():
    with open('recipes.json', 'r') as f:
        return f.read()
@app.route('/generate_recipes', methods=['POST'])
def generate_recipes():
    request_data = request.get_json()
    ingredients = request.json.get('ingredients', [])
    openai.api_key = api_key
    cuisine = request_data.get('cuisine', 'Italian')  # Default to Indian if not specified
    spiciness = request_data.get('spiciness', 'Not Spicy')  # Default to Not Spicy if not specified
    allergies = request_data.get('allergies', '')

    
    # Join the ingredients array into a string
    ingredients_list = ', '.join(ingredients)

    # Crafting the prompt
    prompt = f'Given the ingredients: {ingredients_list} and the cuisine type: {cuisine}. Generate a list of potential recipes for {cuisine} cuisine that is {spiciness} that does not have {allergies} as JSON object as follows: name of recipe, ingredients used, outstanding ingredient (ingredients that is in the receipe but not in the list of given ingredients), instruction like this: follows: {{"recipes": [{{"name":, "ingredients":,"outstanding ingredients":, "instruction":}}]}}.'

    try:
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=2000,
            n=1,
            temperature=0.7
        )

        recipes_json  = response.choices[0].text.strip()
        # Save the JSON string to a file
        try:
            with open('recipes.json', 'w') as json_file:
                json_file.write(recipes_json)
            return redirect(url_for('recipe'))
            #return jsonify({"message": "JSON saved successfully"}), 200
            #return jsonify({"ingredients": ingredients, "suggested_recipes": recipes_json.split('\n')})
        except IOError:
            return jsonify({"error": "Failed to save JSON"}), 500
        

    except Exception as e:
        return jsonify({"error": str(e)})
    

if __name__ == "__main__":
    app.run(debug=True)
