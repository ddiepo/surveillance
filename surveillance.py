import pipe_watcher, time

def on_change(message, pipe):
    if (message == "on"):
        print ("It's On: " + pipe)
    else:
        print ("It's Off: " + pipe)

my_input = pipe_watcher.PipesWatcher(["/tmp/mypipe1", "/tmp/mypipe2"])
while True:
    my_input.check(on_change)
    time.sleep(1)
