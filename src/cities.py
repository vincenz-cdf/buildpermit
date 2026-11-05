"""Registry of supported jurisdictions.

Each city maps its source columns onto the normalized output fields. Every source here was checked
against the live API on 2026-11-05 (columns and freshness). Run the Actor with ``healthCheck: true``
to re-check all of them.

Normalized field names: permit_number, permit_type, permit_subtype, work_class, description, status,
property_type, address, city, zip, latitude, longitude, applied_date, issue_date, expiration_date,
project_value, contractor_name, contractor_phone, contractor_email, contractor_license,
contractor_address, contractor_city, contractor_state, contractor_zip, applicant_name, owner_name,
record_url, _trade_hints (extra text used only for trade classification).
"""

from __future__ import annotations

from .models import ArcGISSource, CartoSource, City, CkanSource, SocrataSource
from .parsing import contact_of_type, geo, join

CITIES: tuple[City, ...] = (
    # ------------------------------------------------------------------ Socrata
    City(
        key="chicago", name="Chicago", state="IL",
        sources=(SocrataSource("data.cityofchicago.org", "ydr8-5enu", "issue_date"),),
        fields={
            "permit_number": "permit_", "permit_type": "permit_type", "work_class": "review_type",
            "description": "work_description", "status": "permit_status",
            "address": join("street_number", "street_direction", "street_name"),
            "latitude": "latitude", "longitude": "longitude",
            "applied_date": "application_start_date", "issue_date": "issue_date",
            "project_value": "reported_cost",
            "contractor_name": contact_of_type("contact", 15, "CONTRACTOR"),
            "contractor_city": contact_of_type("contact", 15, "CONTRACTOR", "city"),
            "contractor_state": contact_of_type("contact", 15, "CONTRACTOR", "state"),
            "contractor_zip": contact_of_type("contact", 15, "CONTRACTOR", "zipcode"),
            "owner_name": contact_of_type("contact", 15, "OWNER"),
            "applicant_name": "contact_1_name",
            "_trade_hints": join(*(f"contact_{i}_type" for i in range(1, 6))),
        },
    ),
    City(
        key="nyc", name="New York City", state="NY",
        sources=(SocrataSource("data.cityofnewyork.us", "rbx6-tga4", "issued_date"),),
        fields={
            "permit_number": "work_permit", "permit_type": "work_type", "work_class": "filing_reason",
            "description": "job_description", "status": "permit_status",
            "address": join("house_no", "street_name", "borough"), "zip": "zip_code",
            "latitude": "latitude", "longitude": "longitude",
            "applied_date": "approved_date", "issue_date": "issued_date", "expiration_date": "expired_date",
            "project_value": "estimated_job_costs",
            "contractor_name": ("applicant_business_name", join("applicant_first_name", "applicant_last_name")),
            "contractor_license": "applicant_license", "contractor_address": "applicant_business_address",
            "applicant_name": join("filing_representative_first_name", "filing_representative_last_name"),
            "owner_name": ("owner_name", "owner_business_name"),
        },
        notes="DOB NOW approved work permits. 'Contractor' is the permittee (licensed applicant).",
    ),
    City(
        key="los-angeles", name="Los Angeles", state="CA",
        sources=(SocrataSource("data.lacity.org", "pi9x-tg5x", "issue_date"),),
        fields={
            "permit_number": "permit_nbr", "permit_type": "permit_type", "permit_subtype": "permit_sub_type",
            "work_class": "use_desc", "description": "work_desc", "status": "status_desc",
            "property_type": "permit_group", "address": "primary_address", "zip": "zip_code",
            "latitude": "lat", "longitude": "lon",
            "applied_date": "submitted_date", "issue_date": "issue_date", "project_value": "valuation",
            "_trade_hints": lambda r: " ".join(
                t for t, flag in (("solar", r.get("solar")), ("ev charger", r.get("ev"))) if str(flag).upper() in ("Y", "YES", "TRUE")
            ),
        },
    ),
    City(
        key="seattle", name="Seattle", state="WA",
        sources=(SocrataSource("cos-data.seattle.gov", "76t5-zqzr", "issueddate"),),
        fields={
            "permit_number": "permitnum", "permit_type": "permittypedesc", "permit_subtype": "permittypemapped",
            "work_class": "permitclass", "description": "description", "status": "statuscurrent",
            "property_type": "permitclassmapped", "address": "originaladdress1", "city": "originalcity",
            "zip": "originalzip", "latitude": "latitude", "longitude": "longitude",
            "applied_date": "applieddate", "issue_date": "issueddate", "expiration_date": "expiresdate",
            "project_value": "estprojectcost", "contractor_name": "contractorcompanyname",
            "record_url": lambda r: (r.get("link") or {}).get("url") if isinstance(r.get("link"), dict) else r.get("link"),
        },
    ),
    City(
        key="austin", name="Austin", state="TX",
        sources=(SocrataSource("datahub.austintexas.gov", "3syk-w9eu", "issue_date"),),
        fields={
            "permit_number": "permit_number", "permit_type": "permit_type_desc", "permit_subtype": "permit_class",
            "work_class": "work_class", "description": "description", "status": "status_current",
            "property_type": "permit_class_mapped", "address": "original_address1", "city": "original_city",
            "zip": "original_zip", "latitude": "latitude", "longitude": "longitude",
            "applied_date": "applieddate", "issue_date": "issue_date", "expiration_date": "expiresdate",
            # Trade permits leave total_job_valuation blank and fill the per-trade valuation instead.
            "project_value": (
                "total_job_valuation", "building_valuation", "building_valuation_remodel", "total_valuation_remodel",
                "mechanical_valuation", "mechanical_valuation_remodel", "electrical_valuation",
                "electrical_valuation_remodel", "plumbing_valuation", "plumbing_valuation_remodel",
            ),
            "contractor_name": ("contractor_company_name", "contractor_full_name"),
            "contractor_phone": "contractor_phone",
            "contractor_address": join("contractor_address1", "contractor_address2"),
            "contractor_city": "contractor_city", "contractor_zip": "contractor_zip",
            "applicant_name": ("applicant_org", "applicant_full_name"),
            "record_url": lambda r: (r.get("link") or {}).get("url") if isinstance(r.get("link"), dict) else r.get("link"),
            "_trade_hints": "contractor_trade",
        },
    ),
    City(
        key="dallas", name="Dallas", state="TX",
        sources=(SocrataSource("www.dallasopendata.com", "e7gq-4sah", "issued_date", server_date_filter=False, order=":id DESC"),),
        fields={
            "permit_number": "permit_number", "permit_type": "permit_type", "work_class": "land_use",
            "description": "work_description", "address": "street_address", "zip": "zip_code",
            "issue_date": "issued_date", "project_value": "value", "contractor_name": "contractor",
        },
        notes="Dallas stores the issue date as text, so date filtering happens after download.",
    ),
    City(
        key="san-francisco", name="San Francisco", state="CA",
        sources=(SocrataSource("data.sfgov.org", "i98e-djp9", "issued_date"),),
        fields={
            "permit_number": "permit_number", "permit_type": "permit_type_definition", "work_class": "proposed_use",
            "description": "description", "status": "status",
            "address": join("street_number", "street_number_suffix", "street_name", "street_suffix"), "zip": "zipcode",
            "latitude": geo("location", "lat"), "longitude": geo("location", "lon"),
            "applied_date": "filed_date", "issue_date": "issued_date",
            "project_value": ("revised_cost", "estimated_cost"),
            "_trade_hints": lambda r: "reroof" if str(r.get("reroof", "")).upper() in ("Y", "YES", "TRUE") else None,
        },
        notes="San Francisco does not publish contractor names.",
    ),
    City(
        key="baton-rouge", name="Baton Rouge (East Baton Rouge Parish)", state="LA",
        sources=(SocrataSource("data.brla.gov", "7fq7-8j7r", "issueddate"),),
        fields={
            "permit_number": "permitnumber", "permit_type": "permittype", "property_type": "designation",
            "description": "projectdescription", "address": ("streetaddress", "address"), "city": "city1",
            "zip": "zip", "latitude": "lat", "longitude": "long",
            "applied_date": "creationdate", "issue_date": "issueddate", "project_value": "projectvalue",
            "contractor_name": "contractorname", "contractor_address": "contractoraddress",
            "applicant_name": "applicantname", "owner_name": "ownername",
        },
    ),
    City(
        key="cincinnati", name="Cincinnati", state="OH",
        sources=(SocrataSource("data.cincinnati-oh.gov", "uhjb-xac9", "issueddate"),),
        fields={
            "permit_number": "permitnum", "permit_type": "permittype", "permit_subtype": "permittypemapped",
            "work_class": "workclass", "description": "description", "status": "statuscurrent",
            "property_type": "permitclass", "address": "originaladdress1", "city": "originalcity",
            "zip": "originalzip", "latitude": "latitude", "longitude": "longitude",
            "applied_date": "applieddate", "issue_date": "issueddate", "expiration_date": "expiresdate",
            "project_value": "estprojectcostdec", "contractor_name": "companyname", "record_url": "link",
        },
    ),
    City(
        key="new-orleans", name="New Orleans", state="LA",
        sources=(SocrataSource("data.nola.gov", "rcm3-fn58", "issuedate"),),
        fields={
            "permit_number": "numstring", "permit_type": "type", "work_class": "landuse",
            "description": "description", "status": "currentstatus", "property_type": "landuseshort",
            "address": "address", "latitude": geo("location_1", "lat"), "longitude": geo("location_1", "lon"),
            "applied_date": "filingdate", "issue_date": "issuedate", "project_value": "constrval",
            "contractor_name": "contractors", "applicant_name": "applicant", "owner_name": "owner",
        },
    ),
    City(
        key="montgomery-county-md", name="Montgomery County", state="MD",
        sources=(
            SocrataSource("data.montgomerycountymd.gov", "m88u-pqki", "issueddate", fixed={"property_type": "residential"}),
            SocrataSource("data.montgomerycountymd.gov", "i26v-w6bd", "issueddate", fixed={"property_type": "commercial"}),
        ),
        fields={
            "permit_number": "permitno", "permit_type": "applicationtype", "work_class": "worktype",
            "permit_subtype": "usecode", "description": "description", "status": "status",
            "address": join("stno", "predir", "stname", "suffix", "postdir"), "city": "city", "zip": "zip",
            "latitude": geo("location", "lat"), "longitude": geo("location", "lon"),
            "applied_date": "addeddate", "issue_date": "issueddate", "project_value": "declaredvaluation",
        },
    ),
    City(
        key="cambridge-ma", name="Cambridge", state="MA",
        sources=(SocrataSource("data.cambridgema.gov", "qu2z-8suj", "issue_date"),),
        fields={
            "permit_number": "id", "permit_type": "permit_type", "work_class": "proposed_property_use",
            "description": "detailed_description_of_work", "status": "status", "address": "full_address",
            "latitude": "latitude", "longitude": "longitude",
            "applied_date": "applicant_submit_date", "issue_date": "issue_date", "project_value": "total_cost",
            "contractor_name": ("firm_name", "licensed_name"), "applicant_name": "applicant_name",
        },
        notes="Addition/alteration permits.",
    ),
    City(
        key="mesa", name="Mesa", state="AZ",
        sources=(SocrataSource("citydata.mesaaz.gov", "dzpk-hxfb", "issued_date"),),
        fields={
            "permit_number": "permit_number", "permit_type": "permit_type", "work_class": "type_of_work",
            "permit_subtype": "record_type", "description": "description_of_work", "status": "status",
            "address": "property_address", "latitude": "latitude", "longitude": "longitude",
            "applied_date": "opened_date", "issue_date": "issued_date", "project_value": ("total_valuation", "job_value"),
            "contractor_name": "contractor_name", "contractor_phone": "contractor_phone",
            "contractor_email": "contractor_email", "contractor_license": "contractor_license",
            "contractor_address": "contractor_address", "contractor_city": "contractor_city",
            "contractor_state": "contractor_state", "contractor_zip": "contractor_zip", "applicant_name": "applicant",
        },
    ),
    City(
        key="marin-county", name="Marin County", state="CA",
        sources=(SocrataSource("data.marincounty.gov", "mkbn-caye", "issued_date"),),
        fields={
            "permit_number": "permit_number", "permit_type": "type_permit", "work_class": "permit_work_class",
            "permit_subtype": "permit_category", "description": "description", "address": "address",
            "city": "city_town", "zip": "zipcode", "latitude": "latitude", "longitude": "longitude",
            "applied_date": "received_date", "issue_date": "issued_date", "project_value": "construction_value",
            "contractor_name": "contractor", "contractor_address": "contractor_address",
            "contractor_license": "contractor_license",
        },
    ),
    City(
        key="norfolk", name="Norfolk", state="VA",
        sources=(SocrataSource("data.norfolk.gov", "fahm-yuh4", "issue_date"),),
        fields={
            "permit_number": "permit_number", "permit_type": "type", "work_class": "work_type",
            "permit_subtype": "use_type", "description": join("work_type", "structure", "use_type", sep=" - "),
            "status": "status", "property_type": "use_class", "address": "address",
            "latitude": "latitude", "longitude": "longitude",
            "applied_date": "application_date", "issue_date": "issue_date", "expiration_date": "expiration_date",
            "project_value": "project_cost",
        },
    ),
    City(
        key="collin-county-tx", name="Collin County (Plano, Frisco, McKinney, Allen...)", state="TX",
        sources=(SocrataSource("data.texas.gov", "82ee-gbj5", "permitissueddate"),),
        fields={
            "permit_number": "permitnum", "permit_type": "permittypedescr", "permit_subtype": "permitsubtypedescr",
            "description": "permitcomments", "property_type": "proprescom", "address": "situsconcatshort",
            "city": "situscity", "zip": "situszip", "issue_date": "permitissueddate", "project_value": "permitvalue",
            "contractor_name": "permitbuildername", "applicant_name": "permitissuedto", "owner_name": "propownername",
        },
        notes="Collin Central Appraisal District permit feed covering the cities in Collin County.",
    ),
    City(
        key="calgary", name="Calgary", state="AB", country="CA",
        sources=(SocrataSource("data.calgary.ca", "c2es-76ed", "issueddate"),),
        fields={
            "permit_number": "permitnum", "permit_type": "permittype", "permit_subtype": "permittypemapped",
            "work_class": "workclassmapped", "description": "description", "status": "statuscurrent",
            "property_type": "permitclassmapped", "address": "originaladdress",
            "latitude": "latitude", "longitude": "longitude",
            "applied_date": "applieddate", "issue_date": "issueddate", "project_value": "estprojectcost",
            "contractor_name": "contractorname", "applicant_name": "applicantname",
        },
    ),
    City(
        key="edmonton", name="Edmonton", state="AB", country="CA",
        sources=(SocrataSource("data.edmonton.ca", "24uj-dj8v", "issue_date"),),
        fields={
            # Recent Edmonton rows leave permit_number blank; row_id is the stable record id.
            "permit_number": ("permit_number", "row_id"), "permit_type": "job_category", "permit_subtype": "building_type",
            "work_class": "work_type", "description": "job_description", "address": "address",
            "latitude": "latitude", "longitude": "longitude",
            "applied_date": "permit_date", "issue_date": "issue_date", "project_value": "construction_value",
        },
    ),
    # ------------------------------------------------------------------ ArcGIS
    City(
        key="nashville", name="Nashville (Metro Davidson County)", state="TN",
        sources=(ArcGISSource("Date_Issued", layer_url="https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/Building_Permits_Issued_2/FeatureServer/0"),),
        fields={
            "permit_number": "Permit__", "permit_type": "Permit_Type_Description",
            "permit_subtype": "Permit_Subtype_Description", "description": "Purpose", "address": "Address",
            "city": "City", "zip": "ZIP", "latitude": "Lat", "longitude": "Lon",
            "applied_date": "Date_Entered", "issue_date": "Date_Issued", "project_value": "Const_Cost",
            "contractor_name": "Contact",
        },
    ),
    City(
        key="raleigh", name="Raleigh", state="NC",
        sources=(ArcGISSource("issueddate", layer_url="https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services/Building_Permits/FeatureServer/0"),),
        fields={
            "permit_number": "permitnum", "permit_type": "permittypemapped", "permit_subtype": "permittype",
            "work_class": "workclass", "description": ("proposedworkdescription", "description"),
            "status": "statuscurrent", "property_type": "permitclassmapped",
            "address": "originaladdress1", "city": "originalcity", "zip": "originalzip",
            "latitude": "latitude_perm", "longitude": "longitude_perm",
            "applied_date": "applieddate", "issue_date": "issueddate", "expiration_date": "expiresdate",
            "project_value": "estprojectcost",
            "contractor_name": ("contractorcompanyname", "contractordba"), "contractor_phone": "contractorphone",
            "contractor_email": "contractoremail", "contractor_license": ("contractorlicnum", "statelicnum"),
            "contractor_address": join("contractoraddress1", "contractoraddress2"),
            "contractor_city": "contractorcity", "contractor_state": "contractorstate", "contractor_zip": "contractorzip",
            "owner_name": "parcelownername",
        },
    ),
    City(
        key="columbus", name="Columbus", state="OH",
        sources=(ArcGISSource("ISSUED_DT", layer_url="https://services1.arcgis.com/9yy6msODkIBzkUXU/arcgis/rest/services/Building_Permits/FeatureServer/0"),),
        fields={
            "permit_number": "B1_ALT_ID", "permit_type": "B1_PER_TYPE", "permit_subtype": "B1_PER_SUB_TYPE",
            "work_class": "B1_PER_CATEGORY", "description": join("GENERAL_TYPE", "VALUE_DESC", sep=" - "),
            "status": "PERMIT_STATUS", "property_type": "B1_PER_TYPE", "address": "SITE_ADDRESS",
            "zip": "B1_SITUS_ZIP", "issue_date": "ISSUED_DT", "project_value": "G3_VALUE_TTL",
            "contractor_name": ("APPLICANT_BUS_NAME", "APPLICANT_FULL_NAME"), "record_url": "ACA_URL",
        },
    ),
    City(
        key="miami-dade-county", name="Miami-Dade County (unincorporated)", state="FL",
        sources=(ArcGISSource("PermitIssuedDate", layer_url="https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/miamidade_permit_data/FeatureServer/0"),),
        fields={
            "permit_number": "PermitNumber", "permit_type": "PermitType", "work_class": "ApplicationTypeDescription",
            "permit_subtype": "ProposedUseDescription", "description": "DetailDescriptionComments",
            "property_type": "ResidentialCommercial", "address": "PropertyAddress", "city": "City",
            "applied_date": "ApplicationDate", "issue_date": "PermitIssuedDate", "project_value": "EstimatedValue",
            "contractor_name": "ContractorName", "contractor_phone": "ContractorPhone",
            "contractor_license": "ContractorNumber", "contractor_address": "ContractorAddress",
            "contractor_city": "ContractorCity", "contractor_state": "ContractorState", "contractor_zip": "ContractorZip",
            "owner_name": "OwnerName",
            "_trade_hints": join(*(f"CategoryDescription{i}" for i in range(1, 11))),
        },
    ),
    City(
        key="miami", name="Miami (city)", state="FL",
        sources=(ArcGISSource("IssuedDate", layer_url="https://services1.arcgis.com/CvuPhqcTQpZPT9qY/arcgis/rest/services/Building_Permits_Since_2014/FeatureServer/0"),),
        fields={
            "permit_number": "PermitNumber", "permit_type": "ScopeofWork", "description": "WorkItems",
            "status": "BuildingPermitStatusDescription", "property_type": "PropertyType",
            "address": "DeliveryAddress", "latitude": "Latitude", "longitude": "Longitude",
            "applied_date": "FirstSubmissionDate", "issue_date": "IssuedDate", "project_value": "TotalCost",
            "contractor_name": "CompanyName", "contractor_address": "CompanyAddress",
            "contractor_city": "CompanyCity", "contractor_zip": "CompanyZip",
        },
    ),
    City(
        key="cleveland", name="Cleveland", state="OH",
        sources=(ArcGISSource("ISSUE_DATE", layer_url="https://services3.arcgis.com/dty2kHktVXHrqO8i/arcgis/rest/services/Building_Permits/FeatureServer/0"),),
        fields={
            "permit_number": "PERMIT_ID", "permit_type": "PERMIT_CATEGORY", "permit_subtype": "PERMIT_SUBTYPE",
            "work_class": "PERMIT_TYPE", "description": ("WORK_DESCRIPTION", "JOB_DESCRIPTION"),
            "status": "CURRENT_TASK_STATUS", "property_type": "PERMIT_CATEGORY", "address": "PRIMARY_ADDRESS",
            "latitude": "LAT", "longitude": "LON", "applied_date": "FILE_DATE", "issue_date": "ISSUE_DATE",
            "project_value": "JOB_VALUE", "contractor_name": ("CONTRATOR_BUSINESS_NAME", "CONTRACTOR_NAME"),
            "contractor_license": "CONTRATOR_LICENSE_ID", "record_url": "ACCELA_CITIZEN_ACCESS_URL",
        },
    ),
    City(
        key="detroit", name="Detroit", state="MI",
        sources=(ArcGISSource("issued_date", layer_url="https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/bseed_building_permits/FeatureServer/0"),),
        fields={
            "permit_number": "record_id", "permit_type": "permit_type", "work_class": "proposed_use_type",
            "permit_subtype": "construction_type", "description": "work_description",
            "property_type": "proposed_use_type", "address": "address", "zip": "zip_code",
            "latitude": "latitude", "longitude": "longitude", "applied_date": "submitted_date",
            "issue_date": "issued_date", "project_value": "amt_estimated_contractor_cost",
        },
    ),
    City(
        key="washington-dc", name="Washington", state="DC",
        sources=(ArcGISSource(
            "ISSUE_DATE",
            service_url="https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer",
            layer_name_template="Building Permits - {year}",
        ),),
        fields={
            "permit_number": "PERMIT_ID", "permit_type": "PERMIT_TYPE_NAME", "permit_subtype": "PERMIT_SUBTYPE_NAME",
            "work_class": "PERMIT_CATEGORY_NAME", "description": "DESC_OF_WORK", "status": "APPLICATION_STATUS_NAME",
            "address": "FULL_ADDRESS", "zip": "ZIPCODE", "latitude": "LATITUDE", "longitude": "LONGITUDE",
            "issue_date": "ISSUE_DATE", "applicant_name": "PERMIT_APPLICANT", "owner_name": "OWNER_NAME",
        },
        notes="DC publishes one layer per year; the right yearly layers are picked from the date range.",
    ),
    City(
        key="baltimore", name="Baltimore", state="MD",
        sources=(ArcGISSource("IssuedDate", layer_url="https://baltegis.baltimorecity.gov/mapping/rest/services/Housing/DHCD_Open_Baltimore_Datasets/FeatureServer/3"),),
        fields={
            "permit_number": "CaseNumber", "permit_type": "PermitName", "work_class": "ProposedUse",
            "description": "Description", "property_type": "ProposedUse", "address": "Address",
            "issue_date": "IssuedDate", "expiration_date": "ExpirationDate", "project_value": "Cost",
        },
    ),
    City(
        key="anaheim", name="Anaheim", state="CA",
        sources=(ArcGISSource("permitissued", layer_url="https://services3.arcgis.com/hPs600I3X0RTaaaq/arcgis/rest/services/Accela_Building_Permits/FeatureServer/0"),),
        fields={
            "permit_number": "casenumber", "permit_type": "typeofwork", "description": "description",
            "status": "casestatus", "property_type": "comres", "address": "address",
            "applied_date": "applicationreceived", "issue_date": "permitissued", "project_value": "jobvaluation",
            "contractor_name": "contractorsname", "contractor_phone": "contractorsphone",
        },
    ),
    # ------------------------------------------------------------------ CKAN
    City(
        key="boston", name="Boston", state="MA",
        sources=(CkanSource("https://data.boston.gov", "6ddcd912-32a0-43df-9908-63574f8c7e77", "issued_date"),),
        fields={
            "permit_number": "permitnumber", "permit_type": "permittypedescr", "work_class": "worktype",
            "description": join("description", "comments", sep=" - "), "status": "status",
            "property_type": "occupancytype", "address": "address", "city": "city", "zip": "zip",
            "latitude": "y_latitude", "longitude": "x_longitude", "issue_date": "issued_date",
            "expiration_date": "expiration_date", "project_value": "declared_valuation", "applicant_name": "applicant",
        },
    ),
    City(
        key="san-antonio", name="San Antonio", state="TX",
        sources=(CkanSource("https://data.sanantonio.gov", "c21106f9-3ef5-4f3a-8604-f992b4db7512", "DATE ISSUED"),),
        fields={
            "permit_number": "PERMIT #", "permit_type": "PERMIT TYPE", "work_class": "WORK TYPE",
            "description": "PROJECT NAME", "address": "ADDRESS", "applied_date": "DATE SUBMITTED",
            "issue_date": "DATE ISSUED", "project_value": "DECLARED VALUATION", "applicant_name": "PRIMARY CONTACT",
        },
    ),
    # ------------------------------------------------------------------ Carto
    City(
        key="philadelphia", name="Philadelphia", state="PA",
        sources=(CartoSource("https://phl.carto.com", "permits", "permitissuedate"),),
        fields={
            "permit_number": "permitnumber", "permit_type": "permittype", "permit_subtype": "permitdescription",
            "work_class": "typeofwork", "description": ("approvedscopeofwork", "permitdescription"),
            "status": "status", "property_type": "commercialorresidential", "address": "address", "zip": "zip",
            "issue_date": "permitissuedate", "contractor_name": "contractorname",
            "contractor_address": join("contractoraddress1", "contractoraddress2"),
            "contractor_city": "contractorcity", "contractor_state": "contractorstate", "contractor_zip": "contractorzip",
            "owner_name": "opa_owner",
        },
        notes="Philadelphia does not publish project valuations.",
    ),
)

CITY_BY_KEY: dict[str, City] = {c.key: c for c in CITIES}
