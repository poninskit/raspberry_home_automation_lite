from flask import Flask, send_from_directory 
from flask_restx import Api, Resource, fields
from flask_socketio import SocketIO, emit
import RPi.GPIO as GPIO


app = Flask(__name__)
#app.config['SECRET_KEY'] = 'my_secret_key'

#Initilize Flask-SocketIO
socketio = SocketIO(app, cors_allowed_origins = "*")

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

api = Api(app,
          version='1.0',
          title='RESTful Pi',
          description='A RESTful API to control the GPIO pins of a Raspbery Pi',
          doc='/docs')

ns = api.namespace('pins', description='Pin related operations')

pin_model = api.model('pins', {
    'id': fields.Integer(readonly=True, description='The pin unique identifier'),
    'pin_num': fields.Integer(required=True, description='GPIO pin associated with this endpoint'),
    'function': fields.String(required=True, description='PIN function'),
    'state': fields.String(required=True, description='low or high')
})



#Broadcast state changes to all connected clients
def broadcast_state_change(pin_num, state):
    """Broadcast pin state changes to all connected clients."""
    socketio.emit('state_update', {'pin_num': pin_num, 'state': state}, room=None)


class PinUtil(object):
    def __init__(self):
        self.counter = 0
        self.pins = []

    def get(self, id):
        for pin in self.pins:
            if pin['id'] == id:
                # Read the actual GPIO state
                actual_state = GPIO.input(pin['pin_num'])  # Get the actual state of the pin
                pin['state'] = 'high' if actual_state == GPIO.HIGH else 'low'  # Set the state as 'high' or 'low'
                return pin
        api.abort(404, f"pin {id} doesn't exist.")

    def create(self, data):
        pin = data
        pin['id'] = self.counter = self.counter + 1
        self.pins.append(pin)
        GPIO.setup(pin['pin_num'], GPIO.OUT)

        #set initial state of the pin in GPIO
        if pin['state'] == 'low':
            GPIO.output(pin['pin_num'], GPIO.LOW)
        elif pin['state'] == 'high':
            GPIO.output(pin['pin_num'], GPIO.HIGH)

        #Broadcast the state change to all connected clients
        broadcast_state_change(pin['pin_num'], pin['state'])

        return pin

    def update(self, id, data):
        pin = self.get(id)
        pin.update(data)  # this is the dict_object update method
        GPIO.setup(pin['pin_num'], GPIO.OUT)

        #update the GPIO pin state
        if pin['state'] == 'low':
            GPIO.output(pin['pin_num'], GPIO.LOW)
        elif pin['state'] == 'high':
            GPIO.output(pin['pin_num'], GPIO.HIGH)

        #Broadcast the state change to all connected clients
        broadcast_state_change(pin['pin_num'], pin['state'])

        return pin

    def delete(self, id):
        pin = self.get(id)
        GPIO.output(pin['pin_num'], GPIO.LOW)
        self.pins.remove(pin)
        
        #Broadcast the state change to all connected clients
        broadcast_state_change(pin['pin_num'], 'deleted')



@ns.route('/')  # keep in mind this our ns-namespace (pins/)
class PinList(Resource):
    """Shows a list of all pins, and lets you POST to add new pins"""

    @ns.marshal_list_with(pin_model)
    def get(self):
        """List all pins"""
        return pin_util.pins

    @ns.expect(pin_model)
    @ns.marshal_with(pin_model, code=201)
    def post(self):
        """Create a new pin"""
        return pin_util.create(api.payload)


@ns.route('/<int:id>')
@ns.response(404, 'pin not found')
@ns.param('id', 'The pin identifier')
class Pin(Resource):
    """Show a single pin item and lets you update/delete them"""

    @ns.marshal_with(pin_model)
    def get(self, id):
        """Fetch a pin given its resource identifier"""
        return pin_util.get(id)

    @ns.response(204, 'pin deleted')
    def delete(self, id):
        """Delete a pin given its identifier"""
        pin_util.delete(id)
        return '', 204

    @ns.expect(pin_model, validate=True)
    @ns.marshal_with(pin_model)
    def put(self, id):
        """Update a pin given its identifier"""
        return pin_util.update(id, api.payload)
    
    @ns.expect(pin_model)
    @ns.marshal_with(pin_model)
    def patch(self, id):
        """Partially update a pin given its identifier"""
        return pin_util.update(id, api.payload)


GPIO.setmode(GPIO.BCM)

pin_util = PinUtil()
pin_util.create({'pin_num': 5, 'function': 'relay_1', 'state': 'high'})   # Channel 1, BCM Pin 5
pin_util.create({'pin_num': 6, 'function': 'relay_2', 'state': 'high'})   # Channel 2, BCM Pin 6
pin_util.create({'pin_num': 13, 'function': 'relay_3', 'state': 'high'})  # Channel 3, BCM Pin 13
pin_util.create({'pin_num': 16, 'function': 'relay_4', 'state': 'high'})  # Channel 4, BCM Pin 16
pin_util.create({'pin_num': 19, 'function': 'relay_5', 'state': 'high'})  # Channel 5, BCM Pin 19
pin_util.create({'pin_num': 20, 'function': 'relay_6', 'state': 'high'})  # Channel 6, BCM Pin 20
pin_util.create({'pin_num': 21, 'function': 'relay_7', 'state': 'high'})  # Channel 7, BCM Pin 21
pin_util.create({'pin_num': 26, 'function': 'relay_8', 'state': 'high'})  # Channel 8, BCM Pin 26


if __name__ == '__main__':
    # Use socketio.run to start the server with broadcast
    socketio.run(app, debug=True, host='0.0.0.0', port=5050)
    
