from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory
import os
from pluto_parser import pluto_parse_file


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploaded_scripts'
app.config['SECRET_KEY'] = 'sdsfhsdkfhdd'  # Required for flash messages

# Create the upload directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def check_pluto(filepath,filename):
    try:
        pluto_parse_file(filepath)
        output_filename = filename.rsplit('.', 1)[0] + '.py'
        old_file = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        new_file = os.path.join(app.config['UPLOAD_FOLDER'], "parsed_pluto_script.py")
        if os.path.exists(old_file):
            if os.path.exists(new_file):
                os.remove(new_file)
            os.rename(old_file, new_file)
            # os.remove(old_file)
        return True
    except Exception as e:
        print(f"Error checking Pluto script: {e}")
        flash(f"Error checking Pluto script: {e}")
        return False


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ["pluto"]

@app.route('/')
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        if check_pluto(filepath,file.filename):
            output_filename = "parsed_pluto_script.py"

            flash('Parsing successful')
            os.remove(filepath)
            return render_template("upload.html", filename=output_filename)
        else:
            flash('Error parsing the file')

        os.remove(filepath)
    else:
        flash('Invalid file type. Only .pluto files are allowed.')

    return redirect(url_for('upload_form'))

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename,as_attachment = True)

if __name__ == '__main__':
    app.run()
