import base64
import os
import re
import shutil

from flask import Flask, request, jsonify, url_for

app = Flask(__name__)

PROJECTS_DIRECTORY = os.environ['PROJECTS_DIRECTORY']
API_RESPONSE_LESS_VERBOSE = 0


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


@app.route("/api/send-results", methods=['POST'])
def send_results_endpoint():
    try:
        content_type = str(request.content_type)
        if content_type is None:
            raise Exception("The request must have a 'Content-Type' of "
                            "'application/json' or 'multipart/form-data'.")
        if (content_type.startswith('application/json')
            or content_type.startswith('multipart/form-data')) is False:
            raise Exception("The request must have a 'Content-Type' of "
                            "'application/json' or 'multipart/form-data'.")

        project_id = resolve_project(request.args.get('project-id'))
        if project_exists(project_id) is False:
            body = {
                'meta_data': {
                    'message': f"No project found for project ID {project_id}."
                }
            }
            resp = jsonify(body)
            resp.status_code = 404
            return resp

        validated_results = []
        processed_files = []
        failed_files = []
        files = []
        current_files_count = 0
        processed_files_count = 0
        sent_files_count = 0
        results_project = '{}/results'.format(get_project_path(project_id))

        if content_type.startswith('application/json') is True:
            json_body = request.get_json()

            if 'results' not in json_body:
                raise Exception("'results' array is required in the body")

            validated_results = validate_json_results(json_body['results'])
            send_json_results(results_project, validated_results, processed_files, failed_files)

        if content_type.startswith('multipart/form-data') is True:
            validated_results = validate_files_array(request.files.getlist('files[]'))
            send_files_results(results_project, validated_results, processed_files, failed_files)

        failed_files_count = len(failed_files)
        if failed_files_count > 0:
            raise Exception('Problems with files: {}'.format(failed_files))

        if API_RESPONSE_LESS_VERBOSE != 1:
            files = os.listdir(results_project)
            current_files_count = len(files)
            sent_files_count = len(validated_results)
            processed_files_count = len(processed_files)
    except Exception as ex:
        body = {
            'meta_data': {
                'message': str(ex)
            }
        }
        resp = jsonify(body)
        resp.status_code = 400
    else:
        if API_RESPONSE_LESS_VERBOSE != 1:
            body = {
                'data': {
                    'current_files': files,
                    'current_files_count': current_files_count,
                    'failed_files': failed_files,
                    'failed_files_count': failed_files_count,
                    'processed_files': processed_files,
                    'processed_files_count': processed_files_count,
                    'sent_files_count': sent_files_count
                },
                'meta_data': {
                    'message': "Results successfully sent for project_id '{}'".format(project_id)
                }
            }
        else:
            body = {
                'meta_data': {
                    'message': "Results successfully sent for project_id '{}'".format(project_id)
                }
            }

        resp = jsonify(body)
        resp.status_code = 200


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


def resolve_project(project_id_param):
    project_id = None
    if project_id_param is not None:
        project_id = project_id_param
    return project_id


def validate_json_results(results):
    if isinstance(results, list) is False:
        raise Exception("'results' should be an array")

    if not results:
        raise Exception("'results' array is empty")

    map_results = {}
    for result in results:
        if 'file_name' not in result or not result['file_name'].strip():
            raise Exception("'file_name' attribute is required for all results")
        file_name = result.get('file_name')
        map_results[file_name] = ''

    if len(results) != len(map_results):
        raise Exception("Duplicated file names in 'results'")

    validated_results = []
    for result in results:
        file_name = result.get('file_name')
        validated_result = {'file_name': file_name}

        if 'content_base64' not in result or not result['content_base64'].strip():
            raise Exception("'content_base64' attribute is required for '{}' file"
                            .format(file_name))

        content_base64 = result.get('content_base64')
        try:
            validated_result['content_base64'] = base64.b64decode(content_base64)
        except Exception as ex:
            raise Exception(
                "'content_base64' attribute content for '{}' file should be encoded to base64"
                .format(file_name), ex)
        validated_results.append(validated_result)

    return validated_results


def send_json_results(results_project, validated_results, processed_files, failed_files):
    for result in validated_results:
        file_name = result.get('file_name')
        content_base64 = result.get('content_base64')
        file = None
        try:
            file = open("%s/%s" % (results_project, file_name), "wb")
            file.write(content_base64)
        except Exception as ex:
            error = {}
            error['message'] = str(ex)
            error['file_name'] = file_name
            failed_files.append(error)
        else:
            processed_files.append(file_name)
        finally:
            if file is not None:
                file.close()


def validate_files_array(files):
    if not files:
        raise Exception("'files[]' array is empty")
    return files


def send_files_results(results_project, validated_results, processed_files, failed_files):
    for file in validated_results:
        file_name = None
        try:
            file_name = file.filename
            file.save("{}/{}".format(results_project, file_name))
        except Exception as ex:
            error = {}
            error['message'] = str(ex)
            error['file_name'] = file_name
            failed_files.append(error)
        else:
            processed_files.append(file_name)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
