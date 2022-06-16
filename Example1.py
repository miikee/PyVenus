from pyVenus import Connection,Variable,Sequence,Array,Device,Resources

res = Resources()
res.read_layout("Example1.lay")
res.read_liquid_classes(True,False,True,False,False)
res.read_submethods()

from hamilton_resources.deck_layout import DeckLayout
from hamilton_resources.liquid_classes import LiquidClasses
from hamilton_resources.ml_star import Ml_star
from hamilton_resources.channels1mL_8 import Channels1mL_8

con = Connection()

lc = LiquidClasses()
lay = DeckLayout()
star_device = Device(con, lay.layout_file)

smt_star = Ml_star(con)
smt_ch = Channels1mL_8(con)

waste = Sequence(con, "waste", copy=lay.sequences.Waste)
tips1000 = Sequence(con,"tips1000", copy=lay.sequences.MlStar1000ulHighVolumeTipWithFilter)
output_plate = Sequence(con, "output_plate", copy=lay.sequences.output_plate)
buffer = Sequence(con, "buffer", copy=lay.sequences.trough1)

smt_star.Initialize(star_device)
smt_ch.tip_pickup(star_device, tips1000)
while output_plate.current > 0:
    smt_ch.aspirate(star_device, buffer, 500, lc.lcHighVolumeFilter_Water_DispenseSurface_Empty.name, 0)
    smt_ch.dispense(star_device, output_plate, 500)
smt_ch.tip_eject(star_device, waste)

con.close()

