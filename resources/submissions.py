import os

from flask_restful import Resource, reqparse
from gluon.kobo.client import KoboClient
from gluon.inaturalist.client import iNaturalistClient

from transformers.transformers import BUGGY_TRANSFORMERS

class Submissions(Resource):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument(
        'inat_email',
        type=str,
        required=True,
        help='iNaturalist email'
    )
    get_parser.add_argument(
        'inat_password',
        type=str,
        required=True,
        help='iNaturalist password'
    )
    get_parser.add_argument(
        'kobo_username',
        type=str,
        required=True,
        help='Kobo username'
    )
    get_parser.add_argument(
        'kobo_password',
        type=str,
        required=True,
        help='Kobo password'
    )
    get_parser.add_argument(
        'kobo_uid',
        type=str,
        required=True,
        help='uid of Kobo project'
    )

    post_parser = get_parser.copy()
    post_parser.add_argument(
        'submissions',
        type=list,
        required=True,
        help='Submissions to post to iNaturalist'
    )
    post_parser.add_argument(
        'inat_app_id',
        type=str,
        required=True,
        help='iNaturalist application id'
    )
    post_parser.add_argument(
        'inat_app_secret',
        type=str,
        required=True,
        help='iNaturalist application secret'
    )

    def get(self):
        kwargs = Submissions.get_parser.parse_args()
        kobo = KoboClient(kwargs['kobo_username'], kwargs['kobo_password'])
        data = kobo.pull_data(kwargs['kobo_uid'])
        transformed_data = []
        failed = 0
        for entry in data:
            try:
                transformed = {}
                for transformer in BUGGY_TRANSFORMERS:
                    key, value = transformer(entry)
                    transformed[key] = value
                transformed_data.append(transformed)
            except Exception:
                failed += 1
        return transformed_data, 200

    def post(self):
        kwargs = Submissions.post_parser.parse_args()
        kobo = KoboClient(kwargs['kobo_username'], kwargs['kobo_password'])
        inat = iNaturalistClient(
            kwargs['inat_email'], kwargs['inat_password'], 
            kwargs['inat_app_id'], kwargs['inat_app_secret']
        )
        uid = kwargs['kobo_uid']
        transformed_data = kwargs['submissions']
        for record in transformed_data:
            image_paths = []
            instance = record['instance']
            for image in record['images']:
                image_path = f'{uid}_{instance}_{image}'
                kobo.pull_image(
                    image_path, uid, instance, image
                )
                image_paths.append(image_path)
            
            # upload the base observation
            observation_id = inat.upload_base_observation(
                record['taxa'], 
                record['longitude'], 
                record['latitude'], 
                record['ts'], 
                record['positional_accuracy'], 
                record['notes']
            )

            # attach the images
            for image_path in image_paths:
                inat.attach_image(
                    observation_id, image_path
                )
                os.remove(image_path)

            # attach the observation field values
            for field_id, value in record['observation_fields'].items():
                inat.attach_observation_field(
                    observation_id, int(field_id), value
                )

        return transformed_data, 201


