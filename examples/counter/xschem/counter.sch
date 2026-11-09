v {xschem version=3.4.8RC file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {SKY130 HD | 4-bit latch counter} 70 -100 0 0 0.65 0.65 {}
T {Exact standard-cell topology from counter_mapped.v | 10 logic cells + 8 latches} 70 -40 0 0 0.34 0.34 {}
T {INTERFACE} 70 40 0 0 0.32 0.32 {}
C {devices/ipin.sym} 180 100 0 0 {name=p1 lab=clk}
N 180 100 250 100 {}
C {devices/lab_pin.sym} 250 100 0 1 {name=p2 lab=clk}
C {devices/ipin.sym} 430 100 0 0 {name=p3 lab=rst_n}
N 430 100 500 100 {}
C {devices/lab_pin.sym} 500 100 0 1 {name=p4 lab=rst_n}
C {devices/ipin.sym} 680 100 0 0 {name=p5 lab=en}
N 680 100 750 100 {}
C {devices/lab_pin.sym} 750 100 0 1 {name=p6 lab=en}
C {devices/iopin.sym} 1120 100 0 0 {name=p7 lab=VPWR}
N 1070 100 1120 100 {}
C {devices/vdd.sym} 1070 100 0 0 {name=p8 lab=VPWR}
C {devices/iopin.sym} 1510 100 0 0 {name=p9 lab=VGND}
N 1460 100 1510 100 {}
C {devices/gnd.sym} 1460 100 0 0 {name=p10 lab=VGND}
N 1880 100 2000 100 {bus=true}
C {devices/opin.sym} 2000 100 0 0 {name=p11 lab=count[3:0]}
T {VPWR = 1.8 V; VPB = VPWR} 1080 130 0 0 0.27 0.27 {}
T {VGND = 0 V; VNB = VGND} 1470 130 0 0 0.27 0.27 {}
T {COMBINATIONAL NEXT-STATE LOGIC} 170 200 0 0 0.37 0.37 {}
T {MASTER | clk = 0} 1300 200 0 0 0.37 0.37 {}
T {SLAVE | clk = 1} 1680 200 0 0 0.37 0.37 {}
T {OUTPUT} 1970 200 0 0 0.37 0.37 {}
T {BIT 0} 70 180 0 0 0.38 0.38 {}
L 21 70 470 2110 470 {dash=4}
T {BIT 1} 70 500 0 0 0.38 0.38 {}
L 21 70 790 2110 790 {dash=4}
T {BIT 2} 70 820 0 0 0.38 0.38 {}
L 21 70 1110 2110 1110 {dash=4}
T {BIT 3} 70 1140 0 0 0.38 0.38 {}
C {sky130_stdcells/o21ai_0.sym} 650 300 0 0 {name=x_07_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/a21oi_1.sym} 1000 300 0 0 {name=x_08_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/and3_1.sym} 300 620 0 0 {name=x_09_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/o21ai_0.sym} 650 940 0 0 {name=x_10_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/a21oi_1.sym} 1000 940 0 0 {name=x_11_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/a41o_1.sym} 300 1260 0 0 {name=x_12_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/nand2_1.sym} 650 1260 0 0 {name=x_13_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/a31oi_1.sym} 1000 1260 0 0 {name=x_14_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/a21oi_1.sym} 650 620 0 0 {name=x_15_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/nor3b_1.sym} 1000 620 0 0 {name=x_16_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/dlxtn_1.sym} 1420 310 0 0 {name=x_17_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/dlxtn_1.sym} 1420 630 0 0 {name=x_18_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/dlxtn_1.sym} 1420 950 0 0 {name=x_19_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/dlxtn_1.sym} 1420 1270 0 0 {name=x_20_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/dlxtp_1.sym} 1790 310 0 0 {name=x_21_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/dlxtp_1.sym} 1790 630 0 0 {name=x_22_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/dlxtp_1.sym} 1790 950 0 0 {name=x_23_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
C {sky130_stdcells/dlxtp_1.sym} 1790 1270 0 0 {name=x_24_ VGND=VGND VNB=VGND VPB=VPWR VPWR=VPWR prefix=sky130_fd_sc_hd__}
N 730 300 760 300 {}
N 760 300 760 340 {}
N 760 340 920 340 {}
C {devices/lab_wire.sym} 870 340 0 0 {name=p12 lab=_01_}
N 730 940 760 940 {}
N 760 940 760 980 {}
N 760 980 920 980 {}
C {devices/lab_wire.sym} 870 980 0 0 {name=p13 lab=_03_}
N 730 620 940 620 {}
C {devices/lab_wire.sym} 800 620 0 0 {name=p14 lab=_06_}
N 380 1260 450 1260 {}
N 450 1260 450 1280 {}
N 450 1280 590 1280 {}
C {devices/lab_wire.sym} 420 1260 0 0 {name=p15 lab=_04_}
N 710 1260 750 1260 {}
N 750 1260 750 1320 {}
N 750 1320 920 1320 {}
C {devices/lab_wire.sym} 870 1320 0 0 {name=p16 lab=_05_}
N 1080 300 1330 300 {}
C {devices/lab_wire.sym} 1180 300 0 0 {name=p17 lab=_00_[0]}
N 1510 300 1700 300 {}
C {devices/lab_wire.sym} 1660 300 0 0 {name=p18 lab=master[0]}
N 1880 300 2000 300 {}
C {devices/lab_pin.sym} 2000 300 0 1 {name=p19 lab=count[0]}
T {master[0]} 1350 365 0 0 0.27 0.27 {}
T {slave[0] = count[0]} 1710 365 0 0 0.27 0.27 {}
N 1060 620 1330 620 {}
C {devices/lab_wire.sym} 1180 620 0 0 {name=p20 lab=_00_[1]}
N 1510 620 1700 620 {}
C {devices/lab_wire.sym} 1660 620 0 0 {name=p21 lab=master[1]}
N 1880 620 2000 620 {}
C {devices/lab_pin.sym} 2000 620 0 1 {name=p22 lab=count[1]}
T {master[1]} 1350 685 0 0 0.27 0.27 {}
T {slave[1] = count[1]} 1710 685 0 0 0.27 0.27 {}
N 1080 940 1330 940 {}
C {devices/lab_wire.sym} 1180 940 0 0 {name=p23 lab=_00_[2]}
N 1510 940 1700 940 {}
C {devices/lab_wire.sym} 1660 940 0 0 {name=p24 lab=master[2]}
N 1880 940 2000 940 {}
C {devices/lab_pin.sym} 2000 940 0 1 {name=p25 lab=count[2]}
T {master[2]} 1350 1005 0 0 0.27 0.27 {}
T {slave[2] = count[2]} 1710 1005 0 0 0.27 0.27 {}
N 1080 1260 1330 1260 {}
C {devices/lab_wire.sym} 1180 1260 0 0 {name=p26 lab=_00_[3]}
N 1510 1260 1700 1260 {}
C {devices/lab_wire.sym} 1660 1260 0 0 {name=p27 lab=master[3]}
N 1880 1260 2000 1260 {}
C {devices/lab_pin.sym} 2000 1260 0 1 {name=p28 lab=count[3]}
T {master[3]} 1350 1325 0 0 0.27 0.27 {}
T {slave[3] = count[3]} 1710 1325 0 0 0.27 0.27 {}
N 570 260 510 260 {}
C {devices/lab_pin.sym} 510 260 0 0 {name=p29 lab=en}
N 570 300 510 300 {}
C {devices/lab_pin.sym} 510 300 0 0 {name=p30 lab=count[0]}
N 570 340 510 340 {}
C {devices/lab_pin.sym} 510 340 0 0 {name=p31 lab=rst_n}
N 920 260 860 260 {}
C {devices/lab_pin.sym} 860 260 0 0 {name=p32 lab=en}
N 920 300 860 300 {}
C {devices/lab_pin.sym} 860 300 0 0 {name=p33 lab=count[0]}
N 240 580 180 580 {}
C {devices/lab_pin.sym} 180 580 0 0 {name=p34 lab=en}
N 240 620 180 620 {}
C {devices/lab_pin.sym} 180 620 0 0 {name=p35 lab=count[1]}
N 240 660 180 660 {}
C {devices/lab_pin.sym} 180 660 0 0 {name=p36 lab=count[0]}
N 360 620 400 620 {}
N 400 620 400 700 {}
N 400 700 430 700 {}
C {devices/lab_pin.sym} 430 700 0 1 {name=p37 lab=_02_}
N 570 900 510 900 {}
C {devices/lab_pin.sym} 510 900 0 0 {name=p38 lab=count[2]}
N 570 940 510 940 {}
C {devices/lab_pin.sym} 510 940 0 0 {name=p39 lab=_02_}
N 570 980 510 980 {}
C {devices/lab_pin.sym} 510 980 0 0 {name=p40 lab=rst_n}
N 920 900 860 900 {}
C {devices/lab_pin.sym} 860 900 0 0 {name=p41 lab=count[2]}
N 920 940 860 940 {}
C {devices/lab_pin.sym} 860 940 0 0 {name=p42 lab=_02_}
N 220 1180 160 1180 {}
C {devices/lab_pin.sym} 160 1180 0 0 {name=p43 lab=count[2]}
N 220 1220 160 1220 {}
C {devices/lab_pin.sym} 160 1220 0 0 {name=p44 lab=en}
N 220 1260 160 1260 {}
C {devices/lab_pin.sym} 160 1260 0 0 {name=p45 lab=count[1]}
N 220 1300 160 1300 {}
C {devices/lab_pin.sym} 160 1300 0 0 {name=p46 lab=count[0]}
N 220 1330 160 1330 {}
C {devices/lab_pin.sym} 160 1330 0 0 {name=p47 lab=count[3]}
N 590 1240 530 1240 {}
C {devices/lab_pin.sym} 530 1240 0 0 {name=p48 lab=rst_n}
N 920 1200 860 1200 {}
C {devices/lab_pin.sym} 860 1200 0 0 {name=p49 lab=count[2]}
N 920 1240 860 1240 {}
C {devices/lab_pin.sym} 860 1240 0 0 {name=p50 lab=count[3]}
N 920 1280 860 1280 {}
C {devices/lab_pin.sym} 860 1280 0 0 {name=p51 lab=_02_}
N 570 580 510 580 {}
C {devices/lab_pin.sym} 510 580 0 0 {name=p52 lab=en}
N 570 620 510 620 {}
C {devices/lab_pin.sym} 510 620 0 0 {name=p53 lab=count[0]}
N 570 660 510 660 {}
C {devices/lab_pin.sym} 510 660 0 0 {name=p54 lab=count[1]}
N 940 580 880 580 {}
C {devices/lab_pin.sym} 880 580 0 0 {name=p55 lab=_02_}
N 940 660 880 660 {}
C {devices/lab_pin.sym} 880 660 0 0 {name=p56 lab=rst_n}
N 1330 320 1270 320 {}
C {devices/lab_pin.sym} 1270 320 0 0 {name=p57 lab=clk}
N 1330 640 1270 640 {}
C {devices/lab_pin.sym} 1270 640 0 0 {name=p58 lab=clk}
N 1330 960 1270 960 {}
C {devices/lab_pin.sym} 1270 960 0 0 {name=p59 lab=clk}
N 1330 1280 1270 1280 {}
C {devices/lab_pin.sym} 1270 1280 0 0 {name=p60 lab=clk}
N 1700 320 1640 320 {}
C {devices/lab_pin.sym} 1640 320 0 0 {name=p61 lab=clk}
N 1700 640 1640 640 {}
C {devices/lab_pin.sym} 1640 640 0 0 {name=p62 lab=clk}
N 1700 960 1640 960 {}
C {devices/lab_pin.sym} 1640 960 0 0 {name=p63 lab=clk}
N 1700 1280 1640 1280 {}
C {devices/lab_pin.sym} 1640 1280 0 0 {name=p64 lab=clk}
T {OPERATION} 70 1480 0 0 0.35 0.35 {}
T {clk low: master tracks next-state; clk high: slave tracks master. All 8 gate pins use the same clk net.} 70 1525 0 0 0.3 0.3 {}
T {rst_n low: next-state = 0. Otherwise: en high increments modulo 16; en low holds. Reset acts through data logic.} 70 1565 0 0 0.3 0.3 {}
T {Identical labels are electrically connected. count[i] is the slave[i] alias in the Yosys netlist.} 70 1605 0 0 0.3 0.3 {}
T {All standard cells: VPWR / VPB -> VPWR, VGND / VNB -> VGND. Supply connections are symbol attributes.} 70 1645 0 0 0.3 0.3 {}
T {Source: ../counter_mapped.v | Library: sky130_fd_sc_hd | Native xschem schematic} 70 1710 0 0 0.27 0.27 {}
