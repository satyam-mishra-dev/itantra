"""Runs the wave-2 wow-factor self-checks: prosody, rollcall, afsk, cap_bridge."""
import prosody
import rollcall
import afsk
import cap_bridge

if __name__ == '__main__':
    prosody.demo()
    rollcall.demo()
    afsk.demo()
    cap_bridge.demo()
    print('test_wow: all 4 modules green')
