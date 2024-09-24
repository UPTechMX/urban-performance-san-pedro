# Urban Performance - Guía rápida de Instalación

Una herramienta web para la planificación urbana.

## Requisitos
- [Docker](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/linux/)
- La virtualización debe estar permitida en el equipo donde se vaya a instalar.

## Instalación
1. Clone el repositorio de [Urban Performance](https://github.com/UPTechMX/urban-performance-san-pedro) usando git, o, alternativamente, puede descargar el repositorio y descomprimirlo en una carpeta de su preferencia.:
```
      $ git clone https://gitlab.up.technology/uptech/urban-performance
```
2. Localice y clone los archivos ubicados en `.envs/.local/`, personalice los valores y remueva la extensión `.example` a cada uno.
3. Ubique el archivo `local.yml`, se trata del archivo docker compose para la construcción de los contenedores, ajústelo a sus necesidades.
4. Ejecute el siguiente comando en la raíz de la carpeta para comenzar la construcción de los contenedores, esta acción requiere de internet.
```
      $ docker compose -f local.yml build
```
5. Compile el idioma español para que Urban Performance pueda mostrarse en dicho idioma:
```
      $ docker compose -f local.yml run --rm django python manage.py compilemessages -l es_mx
```
6. Una vez terminada la construcción de los contenedores podrá ejecutar el sistema con el siguiente comando:
```
      $ docker compose -f local.yml up -d
```
7. podrá acceder al sistema a través de `localhost`en el puerto `8000`, o el que haya definido en el archivo `local.yml`.
8. Este es el usuario administrador por defecto, puede accederse a través de `/es/admin/`, cambie la contraseña en la sección de Usuarios:
```
email: admin@capsus.mx
contraseña: G@rz@G@rcí@
```

## Para HTTPS
Para acceder a través de https seguir las instrucciones para generar un proxy inverso con apache en el [siguiente sitio](https://www.vultr.com/docs/how-to-configure-apache-as-a-reverse-proxy-with-mod-proxy-54152/?lang=es&utm_source=performance-max-na&utm_medium=paidmedia&obility_id=16876066992&utm_adgroup=&utm_campaign=&utm_term=&utm_content=&gclid=Cj0KCQiA-JacBhC0ARIsAIxybyNzy46DDBNftZkMzMNtDifRRHBlVqF8uYTwlP52U3b0RauaQvmlN64aAuhmEALw_wcB):
