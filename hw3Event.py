class Event:
    def __init__(self, start_time, end_time):
        if start_time >= end_time:
            raise ValueError
        else:
            self.start_time = start_time
            self.end_time = end_time

class Calendar:
    def __init__(self):
        self.__events = []
    
    def get_events(self):
        return self.__events
    
    def add_event(self, event):
        if type(event) is not Event:
            raise TypeError
        else:
            self.__events.append(event)

class AdventCalendar(Calendar):
    def __init__(self, year):
        self._Calendar__events = []
        self.year = year

advent_calendar = AdventCalendar(2022)
print(advent_calendar.get_events())  # This should print the list of events


# def main():
#     calendar = Calendar()
#     print(calendar.get_events())
#     calendar.add_event(Event(10, 20))
#     print(calendar.get_events()[0].start_time)
#     try:
#         calendar.add_event("not an event")
#     except TypeError:
#         print("Invalid event")

# if __name__ == "__main__":
#     main()
