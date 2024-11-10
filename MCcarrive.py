import simpy
import random
import itertools

# Globala variabler
NUM_CARS = 500
GREEN_TIME_NS = 60
GREEN_TIME_EW = 60
RED_TIME = 2
ARRIVAL_MEAN = 3
SIMULATION_TIME = 300
DRIVE_TIME = 1
QUEUE_THRESHOLD = 5
INITIAL_CARS = 1

# Bilnumrering med itertools
car_id_counter = itertools.count(1)

class TrafficLight:
    def __init__(self, env, stats):
        self.env = env
        self.current_state = 'NS'
        self.queue_north = []
        self.queue_east = []
        self.queue_south = []
        self.queue_west = []
        self.stats = stats
        self.env.process(self.green_light_duration(GREEN_TIME_NS))
    
    def run(self):
        while True:
            self.record_queue_lengths()  # Registrera kölängderna
            self.check_queues()
            yield self.env.timeout(1)

    def check_queues(self):
        if (len(self.queue_north) >= QUEUE_THRESHOLD or len(self.queue_south) >= QUEUE_THRESHOLD) and self.current_state != 'NS':
            self.switch_to_ns()
        elif (len(self.queue_east) >= QUEUE_THRESHOLD or len(self.queue_west) >= QUEUE_THRESHOLD) and self.current_state != 'EW':
            self.switch_to_ew()

    def switch_to_ns(self):
        self.current_state = 'NS'
        self.env.process(self.green_light_duration(GREEN_TIME_NS))

    def switch_to_ew(self):
        self.current_state = 'EW'
        self.env.process(self.green_light_duration(GREEN_TIME_EW))

    def green_light_duration(self, duration):
        yield self.env.timeout(duration)
        yield self.env.timeout(RED_TIME)

    def record_queue_lengths(self):
        # Registrera kölängder för alla riktningar
        self.stats['queue_lengths_ns'].append(len(self.queue_north) + len(self.queue_south))
        self.stats['queue_lengths_ew'].append(len(self.queue_east) + len(self.queue_west))


class Car:
    def __init__(self, env, car_id, traffic_light, direction, stats, road):
        self.env = env
        self.car_id = car_id
        self.traffic_light = traffic_light
        self.direction = direction
        self.stats = stats
        self.road = road
        self.arrival_time = None
        self.departure_time = None
        self.queue_time = 0
        self.wait_time = 0

    def drive(self):
        self.arrival_time = self.env.now
        yield self.env.timeout(0)

        if self.direction == 'NORTH':
            self.traffic_light.queue_north.append(self)
            while self.traffic_light.current_state != 'NS':
                yield self.env.timeout(1)
            yield self.env.process(self.cross_intersection())

        elif self.direction == 'EAST':
            self.traffic_light.queue_east.append(self)
            while self.traffic_light.current_state != 'EW':
                yield self.env.timeout(1)
            yield self.env.process(self.cross_intersection())

        elif self.direction == 'SOUTH':
            self.traffic_light.queue_south.append(self)
            while self.traffic_light.current_state != 'NS':
                yield self.env.timeout(1)
            yield self.env.process(self.cross_intersection())

        elif self.direction == 'WEST':
            self.traffic_light.queue_west.append(self)
            while self.traffic_light.current_state != 'EW':
                yield self.env.timeout(1)
            yield self.env.process(self.cross_intersection())

    def cross_intersection(self):
        with self.road.request() as request:
            yield request
            yield self.env.timeout(DRIVE_TIME)

        self.departure_time = self.env.now
        self.queue_time = self.departure_time - self.arrival_time
        self.wait_time = self.queue_time + DRIVE_TIME

        if self.direction == 'NORTH':
            self.traffic_light.queue_north.remove(self)
        elif self.direction == 'EAST':
            self.traffic_light.queue_east.remove(self)
        elif self.direction == 'SOUTH':
            self.traffic_light.queue_south.remove(self)
        elif self.direction == 'WEST':
            self.traffic_light.queue_west.remove(self)

        # Registrera väntetider och kötid i statistik
        self.stats['total_wait_time'] += self.wait_time
        self.stats['queue_times'].append(self.queue_time)
        self.stats['car_count'] += 1


def setup(env, initial_cars, arrival_mean, stats):
    traffic_light = TrafficLight(env, stats)
    road = simpy.Resource(env, capacity=1)
    env.process(traffic_light.run())
    car_count = itertools.count()
    
    # Initiala bilar
    for _ in range(initial_cars):
        env.process(Car(env, f'Car {next(car_count)}', traffic_light, 'NORTH', stats, road).drive())

    # Generera nya bilar
    while True:
        yield env.timeout(random.expovariate(1.0 / arrival_mean))
        env.process(Car(env, f'Car {next(car_count)}', traffic_light, random.choice(['NORTH', 'EAST', 'SOUTH', 'WEST']), stats, road).drive())


# Huvudprogram för att köra simuleringen 20 gånger
num_simulations = 20
for i in range(num_simulations):
    env = simpy.Environment()
    stats = {
        'total_wait_time': 0,
        'car_count': 0,
        'wait_times': [],
        'queue_times': [],
        'queue_lengths_ns': [],  # Kölängder för NS-riktning
        'queue_lengths_ew': []   # Kölängder för EW-riktning
    }
    env.process(setup(env, INITIAL_CARS, ARRIVAL_MEAN, stats))
    env.run(until=SIMULATION_TIME)

    # Beräkna resultat för varje körning
    if stats['car_count'] > 0:
        average_queue_time = sum(stats['queue_times']) / len(stats['queue_times']) if stats['queue_times'] else 0
        average_queue_length_ns = sum(stats['queue_lengths_ns']) / len(stats['queue_lengths_ns']) if stats['queue_lengths_ns'] else 0
        average_queue_length_ew = sum(stats['queue_lengths_ew']) / len(stats['queue_lengths_ew']) if stats['queue_lengths_ew'] else 0
        print(f'run {i + 1}:')
        print(f'  Medelkötid: {average_queue_time:.2f} sekunder')
        print(f'  Medelkölängd NS: {average_queue_length_ns:.2f} bilar')
        print(f'  Medelkölängd EW: {average_queue_length_ew:.2f} bilar')
    else:
        print(f"Körning {i + 1}: Inga bilar passerade korsningen.")
