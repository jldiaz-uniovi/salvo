from aiohttp import FormData
import sys

# Primera implementación, carga datos por defecto
def form(*args):
    img = "perro-robot.jpg"
    data = FormData()
    data.add_field('file',
                open("perro-robot.jpg", 'rb'),
                filename=img,
                content_type='image/jpeg')
    data.add_field('model', "s")
    data.add_field("augment", "false")
    data.add_field("tipo", "imagen")
    data()  # Esta llamada "procesa" todo el formulario y devuelve el Payload, 
            # pero también lo almacena en data._writer
    
    # Ahora retorno por separado las cabeceras y el writer en sí
    return data._writer.headers, data._writer

# Segunda implementación, carga datos de lo que reciba en args
def form(method, url, opts):
    try:
        if not opts.get("data_args"):
            print("ERROR: Es necesario especificar parámetros para el formulario mediante --data-args", file=sys.stderr)
            raise ValueError("No data_args in opts")
        args = dict(a.split(":") for a in opts.get("data_args").split())
        data = FormData()
        for k, v in args.items():
            if k == "file":
                data.add_field("file", open(v, "rb"), filename=v)
            else:
                data.add_field(k, v)
        data()  # Process the form and generate the header and the Payload
        return data._writer.headers, data._writer
    except Exception as e:
        print("EXCEPCION:", e)
