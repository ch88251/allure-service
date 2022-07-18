import os
import re
import shutil

from flask import Flask, request, jsonify, url_for

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


@app.route('/api/projects/<project_id>')
def get_project_endpoint(project_id):
    try:
        if project_exists(project_id) is False:
            body = {
                'meta_data': {
                    'message': "project_id '{}' not found".format(project_id)
                }
            }
            resp = jsonify(body)
            resp.status_code = 404
            return resp

        project_path = get_project_path(project_id)
        project_reports_path = f'{project_path}/reports'

        reports_entity = []

        for file in os.listdir(project_reports_path):
            file_path = f'{project_reports_path}/{file}/index.html'
            is_file = os.path.isfile(file_path)
            if is_file is True:
                report = url_for('get_reports_endpoint', project_id=project_id,
                                 path='{file}/index.html', _external=True)
                reports_entity.append([report, os.path.getmtime(file_path), file])
        reports_entity.sort(key=lambda reports_entity: reports_entity[1], reverse=True)
        reports = []
        reports_id = []
        latest_report = None

        for report_entity in reports_entity:
            link = report_entity[0]
            if report_entity[2].lower() != 'latest':
                reports.append(link)
                reports_id.append(report_entity[2])
            else:
                latest_report = link

        if latest_report is not None:
            reports.insert(0, latest_report)
            reports_id.insert(0, 'latest')
        body = {
            'data': {
                'project': {
                    'id': project_id,
                    'reports': reports,
                    'reports_id': reports_id
                },
            },
            'meta_data': {
                'message': "Project successfully obtained"
                }
            }
        resp = jsonify(body)
        resp.status_code = 200
        return resp
    except Exception as ex:
        body = {
            'meta_data': {
                'message': str(ex)
            }
        }
        resp = jsonify(body)
        resp.status_code = 400
        return resp


@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project_endpoint(project_id):
    try:
        if project_exists(project_id) is False:
            body = {
                'message': f"No project found with id {project_id}"
            }
            resp = jsonify(body)
            resp.status_code = 404
            return resp
        project_path = get_project_path(project_id)
        shutil.rmtree(project_path)
    except Exception as ex:
        body = {
            'message': str(ex)
        }
        response = jsonify(body)
        response.status_code = 400
    else:
        body = {
            'message': f'Successfully deleted project with id {project_id}'
        }
        response = jsonify(body)
        response.status_code = 200

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
