"""Modele de date pentru pachetele de documente IGM — "EUROPERSONAL" SRL.

Reguli de business (din analiza exemplelor corecte):
- Numele/Prenumele se preiau EXACT ca în pașaport (nu se re-împart).
- Adresa de cazare vine din Contractul de Comodat/Locațiune — sursă unică.
- Bangladesh: are prenume tată/mamă + adresă permanentă (pagina 2 pașaport).
- Nepal: aceste câmpuri lipsesc -> "-" sau gol, conform exemplelor corecte.
"""
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Country(str, Enum):
    BANGLADESH = "BANGLADESH"
    NEPAL = "NEPAL"


CITIZENSHIP = {Country.BANGLADESH: "BANGLADESHI", Country.NEPAL: "NEPALI"}
DEFAULT_LANGUAGE = {Country.BANGLADESH: "BANGLA", Country.NEPAL: "NEPALI"}
COUNTRY_RO = {Country.BANGLADESH: "Bangladesh", Country.NEPAL: "Nepal"}


class PassportData(BaseModel):
    surname: str = Field(description="Numele — exact ca în pașaport (Surname)")
    given_name: str = Field(description="Prenumele — exact ca în pașaport (Given Name)")
    country: Country
    date_of_birth: date
    place_of_birth: str
    sex: str = "M"
    passport_number: str = Field(description="Complet, ex. A19775898 / PA3098320")
    personal_no: str | None = None
    date_of_issue: date
    date_of_expiry: date
    issuing_authority: str = Field(description="ex. DHAKA / MOFA, DEPARTMENT OF PASSPORTS")
    # Doar Bangladesh (pagina 'Personal Data and Emergency Contact'):
    father_name: str | None = None
    mother_name: str | None = None
    permanent_address: str | None = None

    @property
    def full_name(self) -> str:
        """Ordinea NUME + PRENUME, ex. 'UDDIN MD MAIN'."""
        return f"{self.surname} {self.given_name}".strip()

    @property
    def passport_series(self) -> str:
        """Literele de la început: A19775898 -> 'A', PA3098320 -> 'PA'."""
        return "".join(c for c in self.passport_number if c.isalpha())

    @property
    def passport_no_digits(self) -> str:
        return "".join(c for c in self.passport_number if c.isdigit())

    @property
    def citizenship(self) -> str:
        return CITIZENSHIP[self.country]

    @property
    def country_ro(self) -> str:
        """Numele țării în textele românești: Bangladesh / Nepal."""
        return COUNTRY_RO[self.country]

    @model_validator(mode="after")
    def check_country_rules(self):
        if self.country == Country.BANGLADESH and not self.father_name:
            raise ValueError(
                "Bangladesh: lipsește prenumele tatălui (există pe pagina 2 a pașaportului)."
            )
        return self


class Accommodation(BaseModel):
    """Contract de Comodat/Locațiune — SURSA UNICĂ pentru adresa de cazare."""
    address: str = Field(description="ex. mun. Chișinău, str. București, nr. 83, ap. 9")
    contract_type: str = "locațiune"
    contract_number: str = "F/N"
    contract_date: date


class Employment(BaseModel):
    job_title: str = Field(description="ex. Curier livrator")
    job_title_en: str = Field(default="", description="ex. Delivery courier (pt. CIM bilingv)")
    job_domain: str = Field(default="", description="ex. CURIER")
    occupation_code: str = Field(default="", description="Cod CORM, ex. 962101")
    experience: str = "fără experiență"
    vacancy_request_number: str = Field(default="", description="ex. 891")
    vacancy_request_date: date | None = None
    languages: str | None = None
    # Salariu CIM — valori implicite din exemplul corect (editabile ulterior)
    salary_ro: str = "8.700,00 MDL (opt mii șapte sute lei, 00 bani)"
    salary_en: str = "8,700.00 MDL (eight thousand seven hundred lei, 00 bani)"


class PackageMeta(BaseModel):
    demers_number: str = Field(default="", description="ex. 8B/25")
    demers_date: date | None = None
    cim_number: str = Field(default="", description="ex. 8B/26")
    cim_date: date | None = None
    civil_status: str = "Necăsătorit"
    family_reunification: bool = False
    residence_request: str = "Acordare"


class WorkerPackage(BaseModel):
    passport: PassportData
    accommodation: Accommodation
    employment: Employment | None = None
    meta: PackageMeta = Field(default_factory=PackageMeta)

    @property
    def languages(self) -> str:
        if self.employment and self.employment.languages:
            return self.employment.languages
        return DEFAULT_LANGUAGE[self.passport.country]


def fmt_date(d: date | None = None) -> str:
    """Formatul folosit în toate documentele: 31.10.2025."""
    return d.strftime("%d.%m.%Y") if d else ""
