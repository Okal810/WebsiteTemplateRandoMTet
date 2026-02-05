from mvg import MvgApi

def main():
    print("Testing MVG API (Debug)...")
    
    try:
        # 1. Get Station ID
        station = MvgApi.station('Buchenau')
        if station:
            s_id = station['id']
            api = MvgApi(s_id)
            deps = api.departures()
            
            if deps:
                print(f"Found {len(deps)} departures")
                print(f"Type of first item: {type(deps[0])}")
                print(f"First item content: {deps[0]}")
                
                # Check for attributes if it's an object
                d = deps[0]
                if hasattr(d, '__dict__'):
                    print(f"Attributes: {d.__dict__}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
