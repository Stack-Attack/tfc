from tfc import TFC

tfc = TFC()

final, transition, vis = tfc.process_TFC('samples/dj1.ogg', 'samples/dj2.ogg', 1)

tfc.write_audio('final.wav', final)
tfc.write_audio('transition.wav', transition)

with open('visualization.svg', 'wb') as svg:
    svg.write(vis.getvalue())
