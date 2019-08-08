# ursh
### A URL shortening REST microservice

## Installation

```sh
git clone git@github.com:indico/ursh.git
cd ursh
pip install -e .
```

## Running (development)

```sh
FLASK_APP=ursh.core.app flask run
```

## Running tests

First, install the package with support for testing:

```sh
pip install -e .[testing]
```

Then you can run the tests:

```sh
pytest .
```

## Documentation

* [Documentation for the REST API](https://indico.github.io/ursh), based on the OpenAPI spec

---


|||
|-|-|
|<a href="https://home.cern"><img src="https://design-guidelines.web.cern.ch/sites/design-guidelines.web.cern.ch/files/u6/CERN-logo.jpg" width="64"></a>|Made at [CERN](https://home.cern)<br>[Take part!](https://careers.cern/)|
|||

> ### Note
>
> *In applying the MIT license, CERN does not waive the privileges and immunities
> granted to it by virtue of its status as an Intergovernmental Organization
> or submit itself to any jurisdiction.*
