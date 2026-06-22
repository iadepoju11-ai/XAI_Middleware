from marshmallow import Schema, fields, validate, ValidationError


class ScoreInputSchema(Schema):
    credit_amount    = fields.Integer(required=True, validate=validate.Range(min=1))
    duration         = fields.Integer(required=True, validate=validate.Range(min=1))
    age              = fields.Integer(required=True, validate=validate.Range(min=18, max=120))
    purpose          = fields.String(required=True)
    employment       = fields.String(required=True)
    installment_commitment = fields.Integer(load_default=2, validate=validate.Range(min=1, max=4))
    existing_credits = fields.Integer(load_default=1, validate=validate.Range(min=1))
    sex              = fields.Integer(required=True, validate=validate.OneOf([0, 1]))


class ShapValueSchema(Schema):
    feature = fields.String()
    value   = fields.Float()


class ScoreOutputSchema(Schema):
    application_id  = fields.String()
    decision        = fields.String()
    probability     = fields.Float()
    shap_values     = fields.Dict(keys=fields.String(), values=fields.Float())
    top_factors     = fields.Dict()
    fairness_flags  = fields.Dict(allow_none=True)
    model_version   = fields.String()
    latency_ms      = fields.Float()
