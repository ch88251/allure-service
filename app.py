import os
import re

from flask import Flask, request, jsonify

app = Flask(__name__)

PROJECTS_DIRECTORY = os.environ['PROJECTS_DIRECTORY']


@app.route('/api/projects', methods=['POST'])
def create_project_endpoint():
    try:
        if not request.is_json:
            raise Exception("Header 'Content-Type' is not 'application/json'")

        project_id = create_project(request.get_json())
    except Exception as ex:
        body = {
            'message': str(ex)
        }
        response = jsonify(body)
        response.status_code = 400
    else:
        body = {
            'message': f'Successfully created project with id {project_id}'
        }
        response = jsonify(body)
        response.status_code = 201

    return response


def create_project(json_body):
    if 'id' not in json_body:
        raise Exception('The body should contain an id attribute')
    if isinstance(json_body['id'], str) is False:
        raise Exception('The id should be a string')
    if not json_body['id'].strip():
        raise Exception('The id should not be empty.')
    if len(json_body['id']) > 50:
        raise Exception('The project id cannot be longer than 50 characters.')

    project_id_pattern = re.compile('^[a-z\\d]([a-z\\d -]*[a-z\\d])?$')
    match = project_id_pattern.match(json_body['id'])

    if match is None:
        raise Exception('The project id can only contain alpha-numeric characters and dashes.')

    project_id = json_body['id']

    # Check to see if the project id already exists
    if project_exists(project_id) is True:
        raise Exception(f"A project with id {project_id} already exists.")

    project_path = get_project_path(project_id)
    latest_report_dir = f'{project_path}/reports/latest'
    results_dir = f'{project_path}/results'

    if not os.path.exists(latest_report_dir):
        os.makedirs(latest_report_dir)

    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    return project_id


def project_exists(project_id):
    if not project_id.strip():
        return False
    return os.path.isdir(get_project_path(project_id))


def get_project_path(project_id):
    return f'{PROJECTS_DIRECTORY}/{project_id}'


if __name__ == '__main__':
    app.run(host='0.0.0.0')
