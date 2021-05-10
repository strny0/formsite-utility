import cProfile, pstats, io

def profile(f):
    """Profiler decorator"""
    def inner(*args,**kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        retval = f(*args,**kwargs)
        profiler.disable()
        s = io.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())
        return retval
    
    return inner
