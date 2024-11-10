import simpy
import random
import matplotlib.pyplot as plt

# Globala variabler
NUM_CARS = 500          # Totalt antal bilar som ska simuleras
GREEN_TIME_NS = 60      # Grönt ljus för nord-syd (sekunder)
GREEN_TIME_EW = 60      # Grönt ljus för öst-väst (sekunder)
RED_TIME = 2            # Röd ljus tid (sekunder)
ARRIVAL_MEAN = 3        # Genomsnittlig ankomsttid mellan bilar (sekunder)
SIMULATION_TIME = 100   # Total simuleringstid (sekunder)
DRIVE_TIME = 1          # Tid det tar för en bil att köra igenom korsningen (sekunder)
RUNS = 20               # Antal körningar

class TrafficLight:
    def __init__(self, env):
        self.env = env
        self.state = 'RED'  # Startar med rött ljus
        self.queue_ns = 0   # Kö för nord-syd
        self.queue_ew = 0   # Kö för öst-väst

    def run(self):
        while True:
            # Grönt ljus för nord-syd
            self.state = 'GREEN_NS'
            yield self.env.timeout(GREEN_TIME_NS)

            # Rött ljus för nord-syd
            self.state = 'RED_NS'
            yield self.env.timeout(RED_TIME)

            # Grönt ljus för öst-väst
            self.state = 'GREEN_EW'
            yield self.env.timeout(GREEN_TIME_EW)

            # Rött ljus för öst-väst
            self.state = 'RED_EW'
            yield self.env.timeout(RED_TIME)

class Road:
    def __init__(self, env):
        self.env = env
        self.resource = simpy.Resource(env, capacity=1)  # Endast en bil åt gången kan köra

    def drive(self, car):
        with self.resource.request() as request:
            yield request  # Vänta tills vägen är tillgänglig
            yield self.env.timeout(DRIVE_TIME)  # Tid för att köra genom korsningen

class Car:
    def __init__(self, env, name, traffic_light, road, direction, stats):
        self.env = env
        self.name = name
        self.traffic_light = traffic_light
        self.road = road
        self.direction = direction
        self.queue_time = 0  # Tid i kö
        self.stats = stats  # Referens till statistikobjekt
        self.arrival_time = None  # Tid för ankomst

    def drive(self):
        self.arrival_time = self.env.now  # Registrera ankomsttid

        # Väntar på trafikljus
        if self.direction in ['NORTH', 'SOUTH']:
            self.traffic_light.queue_ns += 1  # Öka kön för nord-syd
            start_queue_time = self.env.now  # Tid när bilen börjar vänta

            # Väntar tills ljuset blir grönt
            while self.traffic_light.state != 'GREEN_NS':
                yield self.env.timeout(1)  # Vänta en sekund och kontrollera igen

            # Registrera tiden i kö
            self.queue_time = self.env.now - start_queue_time
            yield from self.road.drive(self)  # Kör genom korsningen
            self.traffic_light.queue_ns -= 1  # Minska kön för nord-syd

        elif self.direction in ['EAST', 'WEST']:
            self.traffic_light.queue_ew += 1  # Öka kön för öst-väst
            start_queue_time = self.env.now  # Tid när bilen börjar vänta

            # Väntar tills ljuset blir grönt
            while self.traffic_light.state != 'GREEN_EW':
                yield self.env.timeout(1)  # Vänta en sekund och kontrollera igen

            # Registrera tiden i kö
            self.queue_time = self.env.now - start_queue_time
            yield from self.road.drive(self)  # Kör genom korsningen
            self.traffic_light.queue_ew -= 1  # Minska kön för öst-väst

        # Samla statistik för grafer
        self.stats['queue_times'].append(self.queue_time)
        self.stats['queue_ns_lengths'].append(self.traffic_light.queue_ns)
        self.stats['queue_ew_lengths'].append(self.traffic_light.queue_ew)

        # Öka antalet bilar som passerar
        self.stats['car_count'] += 1

def car_generator(env, traffic_light, road, stats):
    directions = ['NORTH', 'EAST', 'SOUTH', 'WEST']
    
    # Generera bilar med en fast riktning i ordning
    for i in range(NUM_CARS):
        direction = random.choice(directions)  # Slumpar riktning
        car = Car(env, f'Bil {i + 1}', traffic_light, road, direction, stats)
        env.process(car.drive())
        
        # Ankomsttid för nästa bil
        yield env.timeout(ARRIVAL_MEAN)  # Tid mellan bilar

# Kör simuleringen flera gånger
for run in range(1, RUNS + 1):
    # Skapa miljön, trafikljus och vägen
    env = simpy.Environment()
    traffic_light = TrafficLight(env)
    road = Road(env)  # Skapa vägen
    stats = {
        'car_count': 0,
        'queue_times': [],          # Lista för att lagra kötid
        'queue_ns_lengths': [],     # Lista för längden på nord-syd kön över tid
        'queue_ew_lengths': []      # Lista för längden på öst-väst kön över tid
    }
    env.process(traffic_light.run())  # Starta trafikljuset
    env.process(car_generator(env, traffic_light, road, stats))  # Starta bilgeneratorn

    # Kör simuleringen fram till 100 sekunder
    env.run(until=SIMULATION_TIME)

    # Beräkna och skriv ut medelvärden för denna körning
    if stats['car_count'] > 0:
        average_queue_time = sum(stats['queue_times']) / len(stats['queue_times']) if stats['queue_times'] else 0
        average_queue_ns_length = sum(stats['queue_ns_lengths']) / len(stats['queue_ns_lengths']) if stats['queue_ns_lengths'] else 0
        average_queue_ew_length = sum(stats['queue_ew_lengths']) / len(stats['queue_ew_lengths']) if stats['queue_ew_lengths'] else 0

        print(f'Run {run}: Medelkötid för bilar: {average_queue_time:.2f} sekunder, '
              f'Medelkölängd NS: {average_queue_ns_length:.2f}, '
              f'Medelkölängd EW: {average_queue_ew_length:.2f}')
    else:
        print(f'Run {run}: Inga bilar har registrerat väntetid.')
