from jwcrypto import jwk, jwt
import typing
import time
from datetime import datetime, timedelta
from sdjwt.didkey import DIDKey
import pytz


def get_current_datetime_in_epoch_seconds_and_iso8601_format(
    delta_in_seconds=0
) -> typing.Tuple[int, str]:
    # Get the current date and time in UTC
    now = datetime.now(pytz.UTC)
    # Increment the current date by the specified number of seconds
    incremented_datetime = now + timedelta(seconds=delta_in_seconds)
    # Format the datetime object in ISO 8601 format
    iso_8601_datetime = incremented_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
    # Calculate the UTC epoch seconds
    epoch_seconds = int(
        (
            incremented_datetime - datetime(1970, 1, 1, tzinfo=pytz.UTC)
        ).total_seconds()
    )
    return epoch_seconds, iso_8601_datetime


def get_alg_for_key(key: jwk.JWK) -> typing.Union[str, None]:
    alg = None
    if key.key_curve == "P-256":
        alg = "ES256"
    return alg


def create_jwt(
    jti: str,
    sub: str,
    iss: str,
    kid: str,
    key: typing.Union[jwk.JWK, None],
    vc: typing.Union[dict, None] = None,
    iat: typing.Union[int, None] = None,
    exp: typing.Union[int, None] = None,
    **kwargs
) -> str:
    header = {"typ": "JWT", "alg": get_alg_for_key(key), "kid": kid}

    iat = iat or int(time.time())
    nbf = iat
    exp = exp or iat + 86400
    claims = {
        "iat": iat,
        "jti": jti,
        "nbf": nbf,
        "exp": exp,
        "sub": sub,
        "iss": iss,
        **kwargs
    }
    if vc:
        claims["vc"] = vc
    token = jwt.JWT(header=header, claims=claims)
    token.make_signed_token(key)

    return token.serialize()


def create_vc_jwt(
    jti: str,
    iss: str,
    sub: str,
    kid: str,
    key: jwk.JWK,
    credential_issuer: str,
    credential_id: str,
    credential_type: typing.List[str],
    credential_context: typing.List[str],
    credential_subject: dict,
    credential_schema: typing.Optional[typing.Union[dict, typing.List[dict]]] = None,
    credential_status: typing.Optional[dict] = None,
    terms_of_use: typing.Optional[typing.Union[dict, typing.List[dict]]] = None,
) -> str:
    expiry_in_seconds = 3600
    issuance_epoch, issuance_8601 = get_current_datetime_in_epoch_seconds_and_iso8601_format()
    expiration_epoch, expiration_8601 = get_current_datetime_in_epoch_seconds_and_iso8601_format(
        expiry_in_seconds
    )
    vc = {
        "@context": credential_context,
        "id": credential_id,
        "type": credential_type,
        "issuer": credential_issuer,
        "issuanceDate": issuance_8601,
        "validFrom": issuance_8601,
        "expirationDate": expiration_8601,
        "issued": issuance_8601,
        "credentialSubject": credential_subject,
    }
    if credential_schema:
        vc["credentialSchema"] = credential_schema
    if credential_status:
        vc["credentialStatus"] = credential_status
    if terms_of_use:
        vc["termsOfUse"] = terms_of_use
    return create_jwt(
        vc=vc,
        jti=jti,
        sub=sub,
        iss=iss,
        kid=kid,
        key=key,
        iat=issuance_epoch,
        exp=expiration_epoch,
    )


def create_w3c_vc_jwt(didkey: DIDKey):
    credential_id = "urn:did:abc"
    credential_type = ["Passport"]
    credential_context = ["https://www.w3.org/2018/credentials/v1"]
    credential_schema = [
        {
            "id": "https://api-conformance.ebsi.eu/trusted-schemas-registry/v2/schemas/z3MgUFUkb722uq4x3dv5yAJmnNmzDFeK5UC8x83QoeLJM",
            "type": "FullJsonSchemaValidator2021",
        }
    ]
    credential_subject = {
        "id": "did:key:datawallet_did",
        "name": "Jane Doe",
        "age": 22
    }

    kid = "did:key:issuer_did#issuer_did"
    jti = credential_id
    iss = "did:key:issuer_did"
    sub = "did:key:datawallet_did"
    to_be_issued_credential = create_vc_jwt(
        credential_id=credential_id,
        credential_type=credential_type,
        credential_context=credential_context,
        credential_subject=credential_subject,
        credential_status=None,
        terms_of_use=None,
        credential_schema=credential_schema,
        kid=kid,
        jti=jti,
        iss=iss,
        sub=sub,
        key=didkey.private_key,
        credential_issuer=didkey.generate()[0],
    )

    return to_be_issued_credential


async def generate_did_key_from_seed(
    crypto_seed: str,
) -> DIDKey:
    crypto_seed_bytes = crypto_seed.encode("utf-8")
    key_did = DIDKey(seed=crypto_seed_bytes)
    return key_did
