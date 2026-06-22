from leadmachine.cvr.mapper import extract_management


def test_extracts_current_management_only(deltager_record) -> None:
    people = extract_management(deltager_record)
    # Jens Hansen is a current adm. dir.; Mette Nielsen's board role ended in 2020
    assert people == [{"name": "Jens Hansen", "role": "adm. dir."}]


def test_empty_when_no_relations() -> None:
    assert extract_management({"Vrvirksomhed": {"cvrNummer": 1}}) == []


def test_dedups_repeated_person_role() -> None:
    rec = {
        "Vrvirksomhed": {
            "deltagerRelation": [
                {
                    "deltager": {"navne": [{"navn": "A B", "periode": {"gyldigTil": None}}]},
                    "organisationer": [
                        {
                            "hovedtype": "LEDELSESORGAN",
                            "organisationsNavn": [{"navn": "Direktion", "periode": {"gyldigTil": None}}],
                            "medlemsData": [
                                {"attributter": [{"type": "FUNKTION", "vaerdier": [
                                    {"vaerdi": "direktør", "periode": {"gyldigTil": None}}
                                ]}]},
                                {"attributter": [{"type": "FUNKTION", "vaerdier": [
                                    {"vaerdi": "direktør", "periode": {"gyldigTil": None}}
                                ]}]},
                            ],
                        }
                    ],
                }
            ]
        }
    }
    assert extract_management(rec) == [{"name": "A B", "role": "direktør"}]
