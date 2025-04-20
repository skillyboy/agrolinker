import subprocess

# Packages to install
packages = [
    "annotated-types==0.7.0",
    "asgiref==3.8.1",
    "certifi==2024.8.30",
    "charset-normalizer==3.3.2",
    "Django==5.1.1",
    "django-cors-headers==4.4.0",
    "django-ninja==1.3.0",
    "djangorestframework==3.15.2",
    "djangorestframework-simplejwt==5.3.1",
    "idna==3.10",
    "pillow==10.4.0",
    "psycopg2-binary==2.9.9",
    "pydantic==2.9.1",
    "pydantic_core==2.23.3",
    "PyJWT==2.9.0",
    "requests==2.32.3",
    "sqlparse==0.5.1",
    "typing_extensions==4.12.2",
    "tzdata==2024.1",
    "urllib3==2.2.3"
]

# Install the packages
for package in packages:
    subprocess.run(["pip", "install", package])
