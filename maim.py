import io
import os
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st


# ----------------------------------------------------------------------------
# EMBEDDED DRUGSTOC BRAND ASSET
# ----------------------------------------------------------------------------
# Embedded from the DrugStoc logo supplied with this dashboard request.
DRUGSTOC_LOGO_B64 = "iVBORw0KGgoAAAANSUhEUgAAAlgAAADICAYAAAA0n5+2AAAiwklEQVR42u3de3Cb9Z3v8e8jWZZlW5bvdhzFNxIcyI0sSQohLWk5ScoSCoVNp7Xb7Szb02k7p6fbdrtnelK2291m2Vm6dKftYbtMl07P1mnnMKS0wIY4LQQICZCkwQkkTmxix1Z8v8myJD+2pN/5w7Gjy2NH8kWxzfs1kxkk29Kj3yP0fPS7fH+aUkoAAAAwd0w0AQAAAAELAACAgAUAAEDAAgAAAAELAACAgAUAAEDAAgAAAAELAACAgAUAAEDAAgAAAAELAACAgAUAAEDAAgAAIGABAACAgAUAAEDAAgAAIGABAACAgAUAAEDAAgAAIGABAACAgAUAAEDAAgAAIGABAACAgAUAAEDAAgAAIGABAAAQsAAAAEDAAgAAIGABAAAQsAAAAEDAAgAAIGABAAAQsAAAAEDAAgAAIGABAAAQsAAAAEDAAgAAIGABAAAQsAAAAAhYAAAAIGABAAAQsAAAAAhYAAAAIGABAAAQsAAAAAhYAAAAIGABAAAQsAAAAAhYAAAAIGABAAAQsAAAAAhYAAAABCwAAAAQsAAAAAhYAAAABCwAAAAQsAAAAAhYAAAABCwAAAAQsAAAAAhYAAAABCwAAAACFgAAAAhYAAAABCwAAAACFgAAAAhYAAAABCwAAAACFgAAAAhYAAAABCwAAAACFgAAAAhYAAAABCwAAAACFgAAAAELAAAABCwAAICFKIUmwGKlB0ISCKrayTezWauxpvCdAQBw42lKKVoBi4JXD9Ze7PFVn2j1yMVun3j0oPjHQpM/t1lMYreaZc2yDLmz3CEVeWkagQsAQMACpghWhy/0Vx++MCAePRj339mtZvnEunzZvjKboAUAIGABE441u1Xtya6EglW0wkyLfOHOElldlK7RogAAAhY+sPRASPaf6lKvNA7G/MxmMcmyrFQpcVhlWVaqpKaYZDQQko6hUWnpGxGXWzf8m3tvyZXda/O1FBM5CwBAwMIHMFz9+DWXOtPujbjfbjXLjqocuXtljuSkpximpEBIiWckqF58r1eOtwzF9HztrMqRT99eRMgCABCw8MERCCl5+s0OdfSSO+L+j67Klk/dVrg/w2quifexBnwB9cuTnXKi1RNx/wPr8uXhDQUkLAAAAQsfDIca+lXtya7xG0rElmqSz28plq0VjhkFokBIycFzfeqZd3oi7v/mR1fIhuWZhCwAwLxgaRUWjAFfQB2oDwtCmswqXImIpJg0uX9tvrbntoKI+5861i5ePVhLqwMACFhY0p55pzuirtUD6/JnFa7C3b82X9tcap+87dGD8nLjQDWtDgAgYGHJanfr6lTbtblSTodVdq/Jm9MhvEc+tGy/3WqevP3Ce330YgEACFhYuo63DEX0Xu3ZWCBzXRw0w2qu2VGVM3nbPxaSiz0+erEAAHOOvQhxw3n1YO3LFwcmbxdmWmRdyfxMQN9Rlbv/4Pn+6okwd6LVIxud9jl5bD0QmvVjmE2aUEJi6QiElARDKmbPTM4zQMAC5t2JNk91eL2qu1dmz9vFJ8NqrqnIs1Wf6/SKKJFTbR4JhNScPN9Tx9pVQ5dvxn9vs5gk1WySLFuKOB2psmZZhtxckJ5QaQrc+ED1fq9fvdvhlcYev/QOj4p/LCSB0LXV2ikmrdpmMUl+Zqo4HamyuSxLbsq3UZsNIGABc3tBqjvfP3nbbjXLx1bl7J/P53Q6UuVcp1dEGx8m9IwE1VSFSxPhHQ2JZyQoMsNHmgyZbl3OdXql7sKA2Cym6oo8W/VHbnLIlrIsLsILlB4IyZGmQfVq46DhTgJG57p7eGzyPBdmWtSO1blyz805Mz7H4SEuLMxxcgACFj6I3u/1q/AL0oblmTLfPTbOnLSoYBSUnPSF+b+Cfywk5zq8cq7TKwfqe9TutfmyrdJB0FpAXIO6+tnxdrnUNzLjx+geHpPak13yauOg+vyHiqWqMPF9M//1SJvqHBqdvJ1qNsnenWX0gAI3CJPccUM9/25vxO0/vTVv3p/TkWaOCVgLmnbtIvz0mx3y2OHLyjWoUyF4AWjo8ql/ONQyq3AVEdbcujzxSpucdnkSOr+BkJJ+b0C6h8cm//X5xjhBwA1EDxZumHa3HrHf4K3FGeLMts5710z4asX59tFV2ZKfYZn2d4IhJcN6UHxjIWl369IxNDrtMTb2+OUfDrXI57cUq7mqE4aZvX9//JpL/KMhw2HhVQU2uW15puRlWCQj1SzWFJPogZB4R4PS7RmVty97DIcT/WMh+ekb7fLornKVjP8fABCwsMQcbxmKuL1rdU5SnrfPG/nNPiPVPG/PdWe5Q1YXJTbcowdC0tI/oi52++Sl8/0xG1aHX4Q9elDtWp3LRfgGeLa+Z/zcRLX+tkqH7LmtUK43r+/B9QXiGtTVr//YJdEbm/vHQvKz4+3ynV3lzKMCFimGCHFDGJVmuLU4IylXko6weSoiIjm2lP0LqW2sKSapKkzX7l+brz3xyZXal+4qkfACqeEO1PfIkaZBhguTzDWoq+hNxEXGdx/44tYSLd5FE85sq/ZX21doD6zLj/nZpb4Rea/Dy7kFCFhA/IxKM8x1YVEjgZCSlrD5MpV5abKQJwFbU0yytcKh/fMnbtofvtXPBP9YSH51qksudPu4ECfRe53emPtWFdjk4Q0FCX9JSDFp8sC6yK2cJrz2/iCNDRCwgPjogVBEaQabxTTvpRkmNPVErlq8fYV9UbRZhtVc8+Vty6/1dKjIkPWLtzp5YyXRxe7Yemf33DzzIe4UkyafXF8Qc//l/pE5KWALgICFD4DmvpGYkJOsXqQX3otctThXVdyTYaKnY2dVTsy8H5dbl2fre+jFigry7W5dtbt1Ndd7Tna4R2Pu21CSOasvCQWZFi16KNijByOqwC9EXj1YO+ALqAFfQBnV4krWuZ44BgIpFsxnNk2AZIsOObvX5CXleQd8AdXY45+8varAJottlVaKSZM9Gwu1pl6/ii4N8PLFAdm9Js9wqLWhy6caeyJ7Xe69Nc+wnla7W1cXe/ziGQmIyPgqx02lWZNt5dWDtYcv9Febw/52o9M+q7Y80jSoJp5PRCQ1xSSJTt4PhJQcveRWJ1uHpHNoVLqHIxYzVNut5uoVOWmypjhddq7O1aLbSQ+E5IX3+iISwpriDMNFCqPByIu4zWKa9ZcEa4pJdlTlyHDY0Lkt1SwpZq0m/BgPnutTQYMc4w5rP5Hxns2XGvqrRWTa/TbvLM+SEkf85841qKsjjQPS1OuXnuGx6EUYqjDTIsVZqbKuJFO2r8zW5mPo36sHa19q6K9u7PFL28BIxDHYLCZlt5olPzNVVhfaZEdVLrXAQMDC0mdUmiH6w/1sX7MSEVmXVzGn4efF93ojyh8kK9jNNWuKST5ze5Hsq7sc09tx8FyfenB97Dyg9zq98tuzvRGBYOfq3MkVahMX7qlKB2SnW8SZbR0Pqv5A9YEzkSHZnpYy+fMZBazGgYhaUoWZFtm1OjehgPbCu73RoSqmfc51euVch1deOt+vdlTlSHhbBYKqNryNRETMmsjqovSYx8q0miOeyz823oMy2x0BjM5dON9oSB083x93qZHo12OkMi9NShzXP3cXun3qN2d6x3dBmMZEHa4z7V753dletanULp+6rXBOQo5XD9b+v3e6q9+M2hw+Olj6x0KTlfIPnu+vvqM8q3qujgGIF0OESKrwlYMiIvfeEnkRrWs9qR4+9Pfy8KG/l7rWk3M23qAHQhFlIZK5anE+VBWmG06KfufK8IxC72OHL6sDZ3rj2uZlPowGZnaqvXqw9p9+36qefrNj2nAVQRsPWwfO9MrfHWxWA77En7wsNy32vd04kJS2SmYdtwnP1veofXWXrxuuYkLtSFBeaRyU7x5srq6/Mjyr/5/rrwyr7x5srn6lcTChNvCPhSaPIdECrgABC4uCVw/Wvn7JPXnb6bDKmmWRIadpqGPyvx87/WsZHvO/MBfPfaRpUIUPI+xYnZuUVYvzaUdVbA/Ppb4RSSQwDPgC6olX2uasEnkyDfgCal/d5epEL/rhCwQu9Y3I439olURDVlVhbK9WXUP/wlvNOcujCYSU/ODlVhVPT9hUYVZkvFfryaNX5FBD/4yO6FBDv3ry6JX4Q7SBbs+Y/PSNdsqaIGkYIkTSnGjzVId/87x7VXZMEcUHK7bKU+f+S3yBEbni7ZNvv/n0fT+86yuzKrYYCCk53nwt2NksJtlSmrXo27MiL02zWUwq+tv8261DcQ2vBYKq9ievuwwvWjaLSfLSr1Wgj95eaCGE9cf/0CquQd2winphpkW2VTqk0J4quekW0TQR32hQXIO6HG8eiuipc7l1+cnrLvnG9hVxP/+Gksz9hZmW6uhhwh+96pI9GwvV9pXZ89I7mmrW9q8qsFUHDSaTG+0AUJmfdt3HtFmmPrc/eLlNTRVgnQ6rbCmzT7bxRJX6S71+Od4yFFMg1z8WktqTXSIiCRXHPdI0qK7+XQy71Sx3lmdJZb5tsmCwdzQoHUOjcrzZHfnevrq5+9NvdkiqWWMXBBCwsDTogZC8ELbvoN1qlm0VjphVVyUZedo3Njykvn9q/EeH2k7K1994Uj12xyMvZlpsu2fy3E09kRPCP1zpkNnOlVkIrCkmuX2FXY6G9QqKjC/tjzfwhk/6t1lMcu8tubKpNEuKs1IX9IbST7/VUe1yx4Yrp8Mqu9fmyZayLMPj3+i0y7235snZ9mH1zOmeyaDV2OOfmBAelwyruaZmU1H1D4+4Iu736EF5+s0OqTvfr7aU2eXulTlz+l7LsJprHt1VXmP0JeJvX2yOWJ1rs5jkWx8rnfG8o1+e6DQMV06HVfZsLJB1JZmGbby1wiF7NhbKkaZBdaC+Jyb01Z7skmJ7qtqwPPO67XKh26eefrMj8k4lYks1yUMbCqadRP/Aunx5+/KQOlDfE/Ml4hdvd0p5bppKZHI/kCiGCJEUDV0+Ff4ht6l06tIM1av+m7ZrxabJ24faTspnDv/jff/3wmE1kyHDyVWLV7/0b1+Vs2Ta1WguUL8vEF+7hAXeyrw0+e7Hy+XB9QWaM9u6oMPVsWa3YRX1zaV22buzbP/WCse0x59i0mSj067t3VkWUby1rqE/oePY6LRrj9yxzPBnLrcuB870ytcONMrfHWxWTx1rV8+/26vqrwzPaM7Xjfj/te5C7JyybZUO2buzbP9Gp33aNrZeXQX66K5ycRpMoP/PE51yvdIZesC4vpsz2yqP7iqXXQYrQaPP89YKh7Z3Z7ncWpwR8TP/WEj+Izq4AXOMHiwkxeELkRev6YawUkyaPHbHIy+KyH2H2k6Of5MddMn3T+2XJ+oP3Lc+r0KVpI///dCYX9qGu6VtuFc+d/M98s3b/iziUz+iNIOWvA2lk8VoC50h//UD1sRKq4lwNZuejmQzCkKbS+3yxa0lCZUEuFq8tUaOXlEnWj0zmjy+fWW25kgzq58d7zDcM1JkfJ5X9By3wkyLKs5KlYo8m6xdliFVhekL6j356z92GbbxI3csSyh8O7Ot2rfuKVX76loiepG6h8fk8IX+6gfXF0z5njvSNKiiF10UZlrkf3xkeUJlJXLSU7Svfnh57b66y9Xhj9fY45fTLo/a6LTTi4V5QQ8W5p1rMKw0gzIuzRAt02Lb/cO7vqL9r42fkvSUa700vsCIvNl1Xg40vyEHmt+Q37v+KBcGXeILjMh/XvxDzKT46NIM0asWF7upNqqOq+CjGh9G+uLWElks4eq0y6MMwoo88qFl+2eyaCHFpMkXt5ZoTsfMS0xsdNq1799XKTurcmLadyoTZQx+e7ZX9tVdlv/9/CX1bH3Pgujdqr8yPGUbz6RnMyc9RfvCnSUGX7oGpqxSrwdCctggSH9uc7HMZFgvw2qu+fMtxTH3H2oYEGC+0IOFeXckfPm6Fn/ISTFp8pe33KvdW7pF/arxFXmu+Q3p8g9O+fufu/keCZ+nZVSawaho5GKWZjGNX8jDXlV0EcwpaePz0RbTPJTo+WYiIg9tKJhVQLSmmGTPxgKJnk+VaIj47OZiuW9Nvnq7dUhOu4YTKmngcuviOqtLXUO/3FGepR5cV3DD5gka7X9Ys6loVm28uihd21bpUOHnz6MH5VSbx3Cy+blOr4qeN7W51C7xzNua7hgeWJev+rzXHtdipvMKBCwsUvGUZriekow87Zu3/Zl8bf3Dcn6gRXV4+6TTfy20lWYWys3ZTinJyIt43KVYmiGaigpXibBZTHLfmvxF9XqjJ/DbrWa5fcXsh3g2Ou1aZV6amm25ipz0FG3X6lzZtTpXBnwBdb7LKx1Do9LY45fmPn/kMKTBuZuo2XSy1SM1m4qSvtItEFLS0OWLaeO5qBl398rsmID8bodXtlY4Yn73vY6ocKqMy5IkaiabcQMELCxI8ZRmiPvNatJkXV6Fti6vIq4LxauNgxFhwmjV4mLnH4ud95NpNcfVxs5s66JaTTngC8T0amwqtc9ZaL5teeac1gPLSU/RwsNDIKSk2zOqWvpHpGNoVM51eiV8FWc4jx6UX7zdKaNBNW8lH4x0e0ZV9Fyyj92cMydtXFWYrhVmWiLOYcsU7d3UG9kuhfal1/sMAhYwq2/D0aUZknWxaOrxR0yQ/XClQ5biNhnuEeOAFY+K3LRF9Vq7PLEbLJfMYu5UtEJ76vx+2Jo0KXFYtYljfnhDgQz4AuropUF5tWkwppSAfywkvzrVJSvzbSpZCzNaDEp8LMuau3Ypy02LeJ0uty56IBQR4AIhJR1Dkee6OCtVgMWGSe6YN51DozGlGZI1RBe9ofRSKs0QrrkvtgckKy2+703OnMUVsPp9sQVR7da5K4CaG1ZYNVly0lO0+9fma/t2V2oPrIsdrvWPheSXUxTZnA/h85Mm5GXMXbvk2GLfm77RyBUZ+lioNnpF51weA0DAwqIX3c1vNNdiPrS7dRU+9LLUSjNMXogCITlpUA/qZoNtXOK92N0oqXGMVNosS/fjyppikoc3FGh7biswDNHJWl04Gpzfp7EZrHqNHuYeDapqAQhYwNRcAyMRPQ035duSEnIONfQv6dIM1y68I8qo9tLmFfa45pqlLbLAkm5wcZ6q9tRMGPWQJdu9t+bFlIzwj4XkfJc3Kc+fGr2qbo7zln80aBCczdHHEPP+HQuyfSAIWMCkgbCClwWZFklGdXCvHqwN79VZiqUZJhgtp6/MS5v3uWZGp3GqekbxGo3qoEk1x340OR3WmAtvvNsCxeNSr/+Gn9MUkyZbyuwx90fPSZovMUNxmvGw4Vx8JoyHK5PY0yJTXYbVXBM99Ds0EhBgsWGSO+Yv7Ixeu+imWZKzWfDRZnd1eK/G7rX5S640g8h48VajmlC3r7DP+3MbbQ7c45l5AAiElLijLqBZBsOXGVZzjdNhjajGfarNI149WDvbUKkHQvLOleG4fvfZ+h4VHToSrXA+HaPJ9kY9P/PhlqIMw+A5F8P7RiUglmWlGn7xKs5KFU/YMH9z34gEQkoW8hZOQMyXUZoAS4VRaYZ4h8sWEz0Qkp+/FbuPmt1qlp2rc+f9CpRq1vZH9zA0z6InyTMSjBnqdDqMV42tKrRFBo+xkBxtds96zs7xlqGYEhBTae7zy9FL7oh/nUOj8zeGlcTRMXuaWSvMjOzFev2S+7r7BsbjbPtwzHlemW8z/N3ovQM9I0F5+/LQrFvCqwdrB3wBFf6PT04QsLDoZKRee3uNjM3/N/APSmmGZ053K6P6STuqcpLSW2e1mGocUSsVXYP6jC/Cb7cOxdw31QpHo56UA/U90u7WZ3yhHPAF1DOnu+P+/WKDHqaTBq9hpmKGAzWRguuUkJirnp0UkxazSMI/FpITbZ5Zh9g/XIzdlmbNsgzD310bfb8m8tr77ll/Mfmb371f/bUDjTLxb19dCx/UIGBh8QlfpdYzPBbf/niz8NzZpV2aIRBS8ssTnaruQuyFqjIvTR5cn5wq1SkmzbAnaaYX4ePNsRfOqWovVRWma+tLMmKe+z/e7JhRwPPqwdp/P9ae0GR5o1Bw9JJ71vPQJs6xUXuUx1GzLHpY1T8WmtGKvD+9NS/mvl+d6prVSsZjze5r+5FeVZhpkXUlxlvfVBWma5V5ka/5XKdXjjQNzvgYond2mC7gAQQsLGjhvRAePTivwyjtbl2F14RaX7K0SjMM+ALq345eMQxXNotJPnN7UVKP587y2J6kZ053J3wRPtbsjtmexm41S3lu2pTn7v61+TElGxp7/PL4y63VifRktbt19cSRtuqJPQOjh8amcmtxhhY9RNo9PCa/eLtz1u/vo5fcMUOV12uPCbnpsfPWWgcSH7p1ZlsNQ+xPXnfNKMRe6PapX7zdGXP/7rX50/a87Vydaxj0LnT7Em5n16CuaqPqidksJtm1emmuMAYBC0tc9PyKwxf65+25okszzMW+ZQuBVw/WHmroV9958ZKcMKh5JSLy+S3FUlWY3JWSFXlpMXN1PHpQ/v1Ye9wX4QvdvpiLnojIJ9ZNvzChqjBd270mqpdFiVzqG5HvvdQiz7/bq6Y7hok23Vd3OWKrmt1r49uX0Zpikk8YFAU9esktP3+rQ820J+tYs1s9/WaHQZjNimvot8ygl+utyzMbuvz0nxQZhtgnjrQlFGLrrwyrH73qkujCoZV5abKtcvp9FrdWOLTouVj+sZD86FWX1F8ZjvsYLnT71GOHL8fcf/sK+6La6BwELGBScVZqxEX4ZKtnTibLGl0wl1JpBq8erK2/Mqyere9R33iuqbr2ZJfhEJbNYpJH7lgmyd4QeCJkPLShICbknOv0yuMvt1ZPdwGcCDhPvNIW87rsVrNsKc267vPfvzZf21YZ1oumXbsAP/NOj3zjuabqH7/mUs+/26uONA2qI02D6lBDv3rqWLthm26rdCS0IGL7yuyYISwRkVcaB+V7B1vUaZcn7qDlGtTVz9/qUD99oz3mZ3arWT65viCu41pTbDx0eazZnXCPjzPbqk2eXxUZsr73UoscauifNsROvKZ/meIcf+HOkrjmjf355qKYav0ePSj/8kqb/PJEp5ou7A34AurZ+h61r+5yzDEUZlqk5vai/QLMI00pFlFg/hxpGoz4Vr6zKkc+u7l4TgPBz9/qUK+ErR585I5lkswNcif80+9b1bkO7+TFXmR8qDKebT7GgkqGRgLSOTQq8axms1vNUrOpKO5w9Wx9j/pt1By1vTvLZtXzFQgp+dcjbTFzayYv0g6r3F5ql0yrWawpJvGMBKRjaFROtXliejQmfH27UzY67dpMz/1MrC/JkL/avkLTx0K1X37mYsScpYfW5085t63drRtevMPP0Z3lWeLMSRNHmnmyvIV/LCjukaD0ecfkbPvwlBtM2ywm+dJdJXG3RyCk5G9fbI5Y6BERIEvtUpCZGlPHLC/Dok3VQzbVnL8Jm0vtUp6bJqlX/35YD173NX1l23LZsDwz7nPc0OVTPzzSNuV75tbiDFldaJPsq1sdeUYCcqHbJ1O9L20Wk3zjoyuS3uuLDx7qYGFebV5h3//M6e7J2lR1FwZkU2mWmqsepvorwxEXWLvVvKBKM5y5EmcFbu1aL5Bcp2VWFdjkL+9YdsOHN1JMmnz5ruX799Vdrja6qLvcurjO6nE/3kPr8xMKVyIif/GhZVpFnk09c7p7RlXdwwO/x2BCuHmaXpYSh1X79o4y9eTrV8To9Xv0oEwXTqZjs5jk81uKE2qPFJMmezYWyA+PuCJ/oMZ7so6+7zZ8b319u1NN9TxX22bKkHWi1TPl0LVR4Pzi1pKEwpWIyOqidO0r25arp6ZYjHCuwysT8+jiPQbCFZKBIULMqwyruaZmU+QE7B+/5hLXoD7rrlPXoK6ePHol4r6aTUULqzSDFue/6KA1RY/QI3csk0d3lWsLZe5IhtVcs3dn2f7oSdGJhok9txXMeBXk9pXZ2j9/4qb9O6ty4t78eX1JhuzdWRbRm+o1KOZpv87G2c5sq7Z3Z9n+iOHKWVpVYJNHd5XPaOh3o9Meu2m0dv331nQ+u7lY+9JdJbPaWHtVgU327ixLOFxN2LA8U9u7s0xWFdim/nIylaufNJV5abM6BiDhj3+GCJEMP3i5NWIoyWYxyde3r5jxXKn6K8PqyaNXIoYNNpfa5asfcd6wD0+jIcLZsllMsqrAJlsrHLOaazUfQ4TRjjQNqrrz/Ya9OdO9tk//SdGcrfgMhJS81+FVZ9uHZcAfEO9oSMaCIbFZTJKVliJluWmypTRLctJjd5c+1uyOnAelRPbuir+NXIO6+s2ZHnm3wzvlcNZ0bVGRZ5Ndq3MS7sWb6ly88G5vXMPN8Q7LevVg7W/O9FQfbxmKu7fQ6bDKzlty53TI/lBDv3q1cTDu95nTYZW7V2XLriQU4QUIWEg6rx6sffzl1urouRkPrMuXj6/O3R9vr5NXD9a+1NBfHR0WKvPS5Ns7yrQbuS3Oj19zqeitQBK9yGZazZJpNUuxPVXWLMuQdSWZc7IFy/Pv9qqXzkeu4vyfdzvnZaikocunTrYOics9KkP+gIwGQ+IfC02+vrwMi6zItsrdK3MMg871RJeCSE81zcl5j57PZbOY5P/suTnh9tcDITneMqQudvuk3xeIaIOJx001myTLliJFdotU5Nlk8wr7/rnuedUDITnSNKjOtg9LvzcQsx3RhESH7QIhJUcvudXFbp90eUbF7Q9MvjZHWopk2VLE6UiVzWVZ8zoU19DlU8db3OIa1COOwWYxSX5mqhTZLXJnuWPJ7kUKAhYQcWF8/A+tMd887VazfPyWXNnotEtBZuyE20BIyfu9fnW+0ysHz/cbLvn+2t0rZnSxxuKiB0Ly3399IeJDa89tBXL/2vxZnXuvHqz9m9+9H7GP5fqSDPnrj5XyngJAwMLC59WDtf/2xpXq6Vb4OLOtUnR1a5Auz6i4BvUph1zWl2TIVz/i1Jbihs4w9tfPNUUU46zMS5Pv7CqfVU/fc2d61IEzkb2iNZuKGFYCQMDC4nKooV/97myv8VyOOFbSFWZaZPfa/BtSjgE3llFphtmEoQvdPrWvLrIQpd1qlic+uZLgDoCAhcVnYj7V8WZ3XJNxJ4LVnRUO2b0mj4vfB1S7W1ffe6klplfzS3eVJLwQYKoaS/ReASBgYdGbmGN14vKQdHpGZVgPyrAelFSzSVJTNMm0mqUizyZrl2XITfm2OZn0jcVtqgKYO6ty5L41+dedjzfgC6iXGwfkt2d7Y3pMr5ZJ4E0GgICFpRm6REQIU5jq/fH9Qy3qUu+I4XDyrcUZsqY4XfIyLJKROl6/yTsaFM/VSuOTcwCjwpXTYZVv3VPKggkABCwAH0xTlf6YKVajAiBgAYCM92T9+lSXev2SO+HinhNsFpN8uNIhn769iOFnAAQsAJjQ7tbVC+/1Sf2V4birjBdmWmTNsgzZtTpXFsrWQwAIWACw4EwsmGjpH5Eez6iMhZSMBcc/4yxmTSwmTQrsqVKem8aCCQAELAAAgMWEQkIAAAAELAAAAAIWAAAAAQsAAAAELAAAAAIWAAAAAQsAAAAELAAAAAIWAAAAAQsAAAAELAAAAAIWAAAAAQsAAICABQAAAAIWAAAAAQsAAICABQAAAAIWAAAAAQsAAICABQAAAAIWAAAAAQsAAICABQAAAAIWAAAAAQsAAICABQAAQMACAAAAAQsAAICABQAAQMACAAAAAQsAAICABQAAQMACAAAAAQsAAICABQAAQMACAAAAAQsAAICABQAAQMACAAAgYAEAAICABQAAQMACAAAgYAEAAICABQAAQMACAAAgYAEAAICABQAAQMACAAAgYAEAAICABQAAQMACAAAgYAEAABCwAAAAQMACAAAgYAEAABCwAAAAQMACAAAgYAEAABCwAAAAEOP/A1Ze6i+xsX2VAAAAAElFTkSuQmCC"


# ----------------------------------------------------------------------------
# PATH CONFIGURATION
# ----------------------------------------------------------------------------
DATA_PATH = r"https://drugstock-my.sharepoint.com/:x:/g/personal/it_drugstoc_com/IQA5yp0kdh82Ra7YcCr-be0vAXufIjkPsYHD4yoBbt6byhs?e=MFF4su&download=1"
IMAGE_PATH = r"C:\Users\IT\OneDrive - DrugStoc\OPERATIONS\LOGISTICS DASH\images (1).png"
CLOUD_IMAGE_PATH = "images (1).png"  # Fallback for Streamlit Cloud deployment

# ----------------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="DrugStoc | Logistics Control Tower",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# CUSTOM CSS WITH HIGH-VISIBILITY KPI CARDS (DARK MODE COMPATIBLE)
# ----------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
        /* ================================================================
           DRUGSTOC DESIGN TOKENS
           The application-level theme is controlled by the sidebar toggle.
           ================================================================ */
        :root {{
            --ds-navy: #073B5C;
            --ds-blue: #5AA6D6;
            --ds-blue-dark: #327EA9;
            --ds-teal: #00A878;
            --ds-green: #18A66A;
            --ds-teal-soft: #E8F8F2;
            --ds-bg: #F5F9FC;
            --ds-surface: #FFFFFF;
            --ds-surface-2: #F1F6F9;
            --ds-border: #D5E2EA;
            --ds-text: #163A50;
            --ds-heading: #073B5C;
            --ds-muted: #5F7787;
            --ds-input: #FFFFFF;
            --ds-shadow: rgba(20, 59, 82, .09);
            --ds-header-start: #073B5C;
            --ds-header-end: #00A878;
        }}

        .stApp {{
            background:
                radial-gradient(circle at 92% 0%, rgba(90,166,214,.12), transparent 24rem),
                linear-gradient(180deg, #F9FCFE 0%, var(--ds-bg) 100%);
            color: var(--ds-text);
        }}

        .block-container {{
            max-width: 1500px;
            padding-top: 1rem;
            padding-bottom: 3rem;
        }}

        /* ---- Universal typography: visible in both modes ---- */
        h1, h2, h3, h4, h5, h6,
        p, label, span, small, div {{
            /* Avoid setting a global color here; component-specific rules below
               keep Streamlit controls readable. */
        }}

        h1, h2, h3 {{
            color: var(--ds-heading) !important;
            font-weight: 800 !important;
            letter-spacing: -.02em;
        }}

        /* ---- Sidebar ---- */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #06243A 0%, #073B5C 100%) !important;
            border-right: 1px solid rgba(255,255,255,.10);
        }}

        section[data-testid="stSidebar"] * {{
            color: #F5FAFD !important;
        }}

        section[data-testid="stSidebar"] .stCaption,
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
            color: #C8DCE8 !important;
        }}

        .ds-sidebar-logo {{
            display: flex;
            justify-content: center;
            align-items: center;
            padding: .7rem .45rem 1rem;
            margin-bottom: .7rem;
            border-bottom: 1px solid rgba(255,255,255,.12);
        }}

        .ds-sidebar-logo img {{
            width: 205px;
            max-width: 90%;
            height: auto;
        }}

        .ds-sidebar-badge {{
            text-align: center;
            padding: .55rem .7rem;
            border: 1px solid rgba(255,255,255,.13);
            border-radius: 12px;
            background: rgba(255,255,255,.07);
            color: #D8EAF3 !important;
            font-size: .72rem;
            font-weight: 750;
            letter-spacing: .55px;
        }}

        /* ---- Main branded header ---- */
        .ds-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.25rem;
            padding: 1.1rem 1.3rem;
            margin: .15rem 0 1rem;
            border-radius: 18px;
            background: linear-gradient(135deg, var(--ds-header-start), var(--ds-header-end));
            box-shadow: 0 12px 30px rgba(7,59,92,.17);
            color: #fff;
        }}

        .ds-header-brand {{
            display: flex;
            align-items: center;
            gap: 1rem;
            min-width: 0;
        }}

        .ds-header-brand img {{
            width: 170px;
            height: auto;
            max-height: 62px;
            object-fit: contain;
            background: rgba(255,255,255,.96);
            border-radius: 10px;
            padding: .35rem .55rem;
        }}

        .ds-header-title {{
            font-size: 1.48rem;
            font-weight: 850;
            line-height: 1.12;
            color: #fff !important;
        }}

        .ds-header-subtitle {{
            margin-top: .3rem;
            color: rgba(255,255,255,.82) !important;
            font-size: .88rem;
        }}

        .ds-header-chip {{
            padding: .48rem .78rem;
            border: 1px solid rgba(255,255,255,.24);
            border-radius: 999px;
            background: rgba(255,255,255,.10);
            color: #fff !important;
            font-size: .75rem;
            font-weight: 800;
            white-space: nowrap;
        }}

        .ds-filter-summary {{
            padding: .68rem .9rem;
            border-radius: 11px;
            background: var(--ds-teal-soft);
            border: 1px solid rgba(0,168,120,.18);
            color: #08664E !important;
            font-size: .8rem;
            margin: .35rem 0 1rem;
        }}

        /* ---- KPI cards ---- */
        div[data-testid="stMetric"] {{
            background: var(--ds-surface) !important;
            border: 1px solid var(--ds-border) !important;
            border-top: 4px solid var(--ds-teal) !important;
            border-radius: 15px !important;
            padding: 1rem 1.05rem !important;
            min-height: 116px;
            box-shadow: 0 7px 20px var(--ds-shadow) !important;
            transition: all .2s ease;
        }}

        div[data-testid="stMetric"]:hover {{
            transform: translateY(-3px);
            box-shadow: 0 13px 28px rgba(20,59,82,.14) !important;
        }}

        div[data-testid="stMetric"] *,
        div[data-testid="stMetricValue"] * {{
            color: var(--ds-text) !important;
        }}

        div[data-testid="stMetricLabel"] *,
        div[data-testid="stMetricLabel"] label,
        div[data-testid="stMetricLabel"] p {{
            color: var(--ds-muted) !important;
            font-size: .74rem !important;
            font-weight: 800 !important;
            text-transform: uppercase !important;
            letter-spacing: .55px !important;
        }}

        div[data-testid="stMetricValue"] * {{
            color: var(--ds-heading) !important;
            font-size: 1.5rem !important;
            font-weight: 850 !important;
        }}

        /* ---- Tabs ---- */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 6px;
            padding: .25rem;
            background: var(--ds-surface-2);
            border: 1px solid var(--ds-border);
            border-radius: 12px;
        }}

        .stTabs [data-baseweb="tab"] {{
            border-radius: 9px;
            padding: .58rem .95rem;
            font-weight: 800;
            color: var(--ds-muted) !important;
        }}

        .stTabs [aria-selected="true"] {{
            background: var(--ds-surface) !important;
            color: var(--ds-teal) !important;
            box-shadow: 0 3px 10px var(--ds-shadow);
        }}

        /* ---- Inputs / selectboxes / uploader ---- */
        div[data-baseweb="select"] > div,
        div[data-testid="stFileUploaderDropzone"] {{
            background: var(--ds-input) !important;
            border-color: var(--ds-border) !important;
            color: var(--ds-text) !important;
        }}

        div[data-baseweb="select"] * {{
            color: var(--ds-text) !important;
        }}

        /* ---- Tables ---- */
        div[data-testid="stDataFrame"] {{
            border: 1px solid var(--ds-border);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 5px 16px var(--ds-shadow);
        }}

        /* ---- Buttons ---- */
        .stButton > button,
        .stDownloadButton > button {{
            border-radius: 9px !important;
            font-weight: 800 !important;
            border: 1px solid var(--ds-border) !important;
        }}

        .stDownloadButton > button {{
            background: var(--ds-navy) !important;
            color: #fff !important;
        }}

        /* ---- Alerts ---- */
        div[data-testid="stAlert"] {{
            border-radius: 12px;
        }}

        @media (max-width: 900px) {{
            .ds-header {{
                align-items: flex-start;
                flex-direction: column;
            }}
            .ds-header-brand img {{
                width: 145px;
            }}
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# DATA LOADING WITH HTTP HEADERS & CACHE (ttl=300)
# ----------------------------------------------------------------------------
@st.cache_data(
    ttl=300, show_spinner="Fetching live logistics data from SharePoint..."
)
def load_data(path=None, uploaded_file=None):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(path, headers=headers, timeout=25)
    response.raise_for_status()

    return pd.read_excel(io.BytesIO(response.content))


def find_col(df, candidates):
    """Safely match column headers even if Excel contains numbers/dates in headers."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None

    cols_lower = {str(c).lower().strip(): c for c in df.columns}

    # 1. Exact match pass
    for cand in candidates:
        cand_str = str(cand).lower().strip()
        if cand_str in cols_lower:
            return cols_lower[cand_str]

    # 2. Substring match pass
    for cand in candidates:
        cand_str = str(cand).lower().strip()
        for col in df.columns:
            if cand_str in str(col).lower().strip():
                return col

    return None


# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# VISUAL HELPERS
# ----------------------------------------------------------------------------
def polish_plot(fig, height=380):
    """Apply a consistent DrugStoc visual language to Plotly charts."""
    fig.update_layout(
        height=height,
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Inter, Arial, sans-serif", color="#102A43"),
        margin=dict(t=35, b=45, l=20, r=20),
        hoverlabel=dict(bgcolor="#071A2B", font_color="white"),
    )
    fig.update_xaxes(showgrid=False, linecolor="#D9E2EA", zeroline=False)
    fig.update_yaxes(gridcolor="#E8EEF2", linecolor="#D9E2EA", zeroline=False)
    return fig


def status_color(status):
    status = str(status).strip().lower()
    if status in {"delivered", "complete", "completed", "successful"}:
        return "#16A34A"
    if status in {"pending", "processing", "in transit", "out for delivery"}:
        return "#F59E0B"
    if status in {"failed", "cancelled", "canceled", "returned", "rejected"}:
        return "#DC2626"
    return "#64748B"


def style_scorecard(dataframe):
    """Conditional formatting: green = better, red = slower/lower."""
    styler = dataframe.style

    if "Delivery Rate %" in dataframe.columns:
        styler = styler.background_gradient(
            subset=["Delivery Rate %"], cmap="RdYlGn", vmin=0, vmax=100
        )

    if "Avg Dispatch Duration (Hrs)" in dataframe.columns:
        styler = styler.background_gradient(
            subset=["Avg Dispatch Duration (Hrs)"], cmap="RdYlGn_r"
        )

    if "Avg Creation-Delivery TAT (Hrs)" in dataframe.columns:
        styler = styler.background_gradient(
            subset=["Avg Creation-Delivery TAT (Hrs)"], cmap="RdYlGn_r"
        )

    return styler


# SIDEBAR HEADER & FILE UPLOADER
# ----------------------------------------------------------------------------
st.sidebar.markdown(
    f"""
    <div class="ds-sidebar-logo">
        <img src="data:image/png;base64,{DRUGSTOC_LOGO_B64}" alt="DrugStoc">
    </div>
    <div class="ds-sidebar-badge">
        LOGISTICS CONTROL TOWER<br>
        <span style="font-weight:600;opacity:.78;">Pharmaceutical Supply Chain</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    """
    <div style="
        padding:.65rem .8rem;
        border:1px solid rgba(255,255,255,.12);
        border-radius:10px;
        background:rgba(255,255,255,.05);
        font-size:.76rem;
        line-height:1.45;">
        <b>Rx Supply Chain</b><br>
        Cold-chain • Distribution • Delivery
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Data Source")
uploaded = st.sidebar.file_uploader(
    "Upload Logistics_DB.xlsx manually", type=["xlsx", "xls"]
)

if st.sidebar.button("🔄 Refresh Data Cache"):
    st.cache_data.clear()
    st.rerun()

# ----------------------------------------------------------------------------
# LOAD RAW DATA & SAFE COLUMN DETECT
# ----------------------------------------------------------------------------
df_raw = None
load_error = None
try:
    df_raw = load_data(
        DATA_PATH if uploaded is None else None, uploaded_file=uploaded
    )
except Exception as e:
    load_error = e

if df_raw is None or not isinstance(df_raw, pd.DataFrame):
    st.error(
        f"Unable to read the dataset from SharePoint.\n\n"
        f"**Details:** {load_error}\n\n"
        "**Quick Fix:** Use the file uploader in the sidebar to select `Logistics_DB.xlsx` from your computer."
    )
    st.stop()

# Clean raw column names to string
df_raw.columns = [str(c).strip() for c in df_raw.columns]

# Auto-detect column headers
auto = {
    "client": find_col(
        df_raw,
        [
            "Client Name",
            "Client",
            "Customer Name",
            "Customer",
            "Pharmacy",
            "Hospital",
        ],
    ),
    "value": find_col(
        df_raw,
        ["Order Value", "Value", "Amount", "Sales Value", "Total Value"],
    ),
    "qty": find_col(
        df_raw,
        [
            "N0 OF CTN'S",
            "NO OF CTN'S",
            "N0 OF CTNS",
            "NO OF CTNS",
            "NO. OF CTNS",
            "Qty CTN",
            "Quantity CTN",
            "Qty (CTN)",
            "Quantity",
            "Qty",
            "Cartons",
            "Carton",
            "CTN",
        ],
    ),
    "created_date": find_col(
        df_raw,
        [
            "Created Date",
            "Creation Date",
            "Order Date",
            "Date Created",
            "Date",
            "Dispatch Date",
        ],
    ),
    "created_time": find_col(
        df_raw,
        [
            "Created Time",
            "Creation Time",
            "Order Time",
            "Time Created",
            "Create Time",
        ],
    ),
    "region": find_col(df_raw, ["Region", "Zone", "State", "Territory"]),
    "status": find_col(df_raw, ["Delivery Status", "Status"]),
    "captain": find_col(
        df_raw,
        ["Captain", "Rider", "Driver", "Captain Name", "Dispatcher"],
    ),
    "order_type": find_col(
        df_raw, ["Order Type", "Type", "Category", "Channel", "Order_Type"]
    ),
    "ship_date": find_col(
        df_raw, ["Ship Date", "Dispatch Date", "Pickup Date"]
    ),
    "dispatch_time": find_col(
        df_raw,
        [
            "Dispatch Time",
            "Ship Time",
            "Time Dispatched",
            "Departure Time",
            "Time Out",
        ],
    ),
    "deliv_date": find_col(
        df_raw, ["Delivery Date", "Delivered Date", "Date Delivered"]
    ),
    "delivery_time": find_col(
        df_raw, ["Delivery Time", "Time Delivered", "Arrival Time", "Time In"]
    ),
}

# ----------------------------------------------------------------------------
# SIDEBAR COLUMN MAPPING PICKER UI
# ----------------------------------------------------------------------------
st.sidebar.markdown("---")
with st.sidebar.expander("🛠️ Data Column Mapping", expanded=False):
    all_cols = ["(none)"] + list(df_raw.columns)

    def picker(label, key):
        default = auto.get(key)
        idx = (
            all_cols.index(default)
            if (default and default in all_cols)
            else 0
        )
        choice = st.selectbox(label, all_cols, index=idx, key=f"map_{key}")
        return None if choice == "(none)" else choice

    col_client = picker("Facility/Client Name", "client")
    col_value = picker("Order Value (₦)", "value")
    col_qty = picker("Quantity (CTN)", "qty")
    col_date = picker("Created Date / Order Date", "created_date")
    col_create_time = picker("Creation Time (Optional)", "created_time")
    col_region = picker("Delivery Zone/Region", "region")
    col_status = picker("Delivery Status", "status")
    col_captain = picker("Logistics Captain", "captain")
    col_order_type = picker("Order Type", "order_type")
    col_ship = picker("Dispatch Date", "ship_date")
    col_dispatch_time = picker("Dispatch Time", "dispatch_time")
    col_deliv = picker("Delivery Date", "deliv_date")
    col_delivery_time = picker("Delivery Time", "delivery_time")

required_missing = [
    n
    for n, v in [
        ("Client Name", col_client),
        ("Order Value", col_value),
        ("Qty CTN", col_qty),
        ("Created/Order Date", col_date),
        ("Region", col_region),
        ("Delivery Status", col_status),
    ]
    if v is None
]

if required_missing:
    st.error(
        f"Missing required mapping for: **{', '.join(required_missing)}**. "
        "Please assign them under 'Data Column Mapping' in the sidebar."
    )
    st.stop()

df = df_raw.copy()

# ----------------------------------------------------------------------------
# DATA CLEANING & TIMESTAMP PARSING
# ----------------------------------------------------------------------------
df[col_date] = pd.to_datetime(df[col_date], errors="coerce")
df = df.dropna(subset=[col_date])
df["Week"] = df[col_date].dt.isocalendar().week.astype(int)
df["Year"] = df[col_date].dt.year.astype(int)
df["Week Label"] = (
    "W" + df["Week"].astype(str).str.zfill(2) + " - " + df["Year"].astype(str)
)

df[col_value] = pd.to_numeric(df[col_value], errors="coerce").fillna(0)
df[col_qty] = pd.to_numeric(df[col_qty], errors="coerce").fillna(0)


def build_timestamp(data_df, date_c, time_c):
    """Combines a date column and an optional time column into a single datetime pandas Series."""
    if not date_c or date_c not in data_df.columns:
        return pd.Series(pd.NaT, index=data_df.index)

    dates = pd.to_datetime(data_df[date_c], errors="coerce")

    if time_c and time_c in data_df.columns:
        times = (
            data_df[time_c]
            .astype(str)
            .str.strip()
            .replace(["nan", "None", "<NaT>", ""], "00:00:00")
        )
        combined_str = dates.dt.strftime("%Y-%m-%d") + " " + times
        return pd.to_datetime(combined_str, errors="coerce")
    return dates


# Construct full Timestamps
df["Created_DT"] = build_timestamp(df, col_date, col_create_time)
df["Delivery_DT"] = build_timestamp(df, col_deliv, col_delivery_time)

dispatch_date_col = (
    col_ship if (col_ship and col_ship in df.columns) else col_date
)
df["Dispatch_DT"] = build_timestamp(df, dispatch_date_col, col_dispatch_time)

# ----------------------------------------------------------------------------
# TAT & DURATION CALCULATIONS (Created_DT to Delivery_DT)
# ----------------------------------------------------------------------------
if col_deliv and col_deliv in df.columns:
    # Creation to Delivery TAT in hours
    tat_hrs = (df["Delivery_DT"] - df["Created_DT"]).dt.total_seconds() / 3600.0
    df["Creation_Delivery_TAT"] = tat_hrs.apply(
        lambda x: x if (pd.notna(x) and x >= 0) else np.nan
    )

    # Dispatch to Delivery Duration in hours
    duration_hrs = (
        df["Delivery_DT"] - df["Dispatch_DT"]
    ).dt.total_seconds() / 3600.0
    df["Dispatch Duration (hrs)"] = duration_hrs.apply(
        lambda x: x if (pd.notna(x) and x >= 0) else np.nan
    )
else:
    df["Creation_Delivery_TAT"] = np.nan
    df["Dispatch Duration (hrs)"] = np.nan

df[col_status] = df[col_status].astype(str).str.strip().str.title()
DELIVERED_LABELS = {"Delivered", "Complete", "Completed", "Successful"}
df["Is Delivered"] = df[col_status].isin(DELIVERED_LABELS)

# ----------------------------------------------------------------------------
# SIDEBAR FILTERS
# ----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Operations Filters")

week_options = ["All Weeks"] + sorted(
    df["Week Label"].unique(),
    key=lambda w: (w.split(" - ")[1], w.split(" - ")[0]),
    reverse=True,
)
selected_week = st.sidebar.selectbox("Filter by Delivery Week", week_options)

region_options = ["All Regions"] + sorted(
    df[col_region].dropna().unique().tolist()
)
selected_region = st.sidebar.selectbox("Filter by Region / Hub", region_options)

if col_order_type and col_order_type in df.columns:
    order_type_options = ["All Order Types"] + sorted(
        df[col_order_type].dropna().astype(str).unique().tolist()
    )
else:
    order_type_options = ["All Order Types"]
selected_order_type = st.sidebar.selectbox(
    "Filter by Order Type", order_type_options
)

status_options = ["All Statuses"] + sorted(
    df[col_status].dropna().unique().tolist()
)
selected_status = st.sidebar.selectbox("Filter by Order Status", status_options)

filtered = df.copy()

if selected_week != "All Weeks":
    filtered = filtered[filtered["Week Label"] == selected_week]

if selected_region != "All Regions":
    filtered = filtered[filtered[col_region] == selected_region]

if (
    selected_order_type != "All Order Types"
    and col_order_type
    and col_order_type in filtered.columns
):
    filtered = filtered[
        filtered[col_order_type].astype(str) == selected_order_type
    ]

if selected_status != "All Statuses":
    filtered = filtered[filtered[col_status] == selected_status]

if filtered.empty:
    st.warning(
        "No pharmaceutical delivery records match the current filter criteria."
    )
    st.stop()

st.sidebar.markdown("---")
st.sidebar.caption(
    f"📦 Total Records: **{len(df):,}** | Filtered Result: **{len(filtered):,}**"
)

# ----------------------------------------------------------------------------
# MAIN DASHBOARD HEADER
# ----------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="ds-header">
        <div class="ds-header-brand">
            <img src="data:image/png;base64,{DRUGSTOC_LOGO_B64}" alt="DrugStoc">
            <div>
                <div class="ds-header-title">Logistics Control Tower</div>
                <div class="ds-header-subtitle">
                    Live pharmaceutical distribution & fulfillment performance
                </div>
            </div>
        </div>
        <div class="ds-header-chip">
            LIVE • {datetime.now().strftime('%d %b %Y, %H:%M')}
        </div>
    </div>
    <div class="ds-filter-summary">
        <b>Active view:</b>
        Week: {selected_week} &nbsp;•&nbsp;
        Region: {selected_region} &nbsp;•&nbsp;
        Order Type: {selected_order_type} &nbsp;•&nbsp;
        Status: {selected_status}
    </div>
    """,
    unsafe_allow_html=True,
)

tab_overview, tab_captains, tab_data = st.tabs(
    [
        "📊 Executive Overview",
        "🧑‍✈️ Captain & Rider Efficiency",
        "🗂️ Audit & Raw Data",
    ]
)

# ============================================================================
# TAB 1: EXECUTIVE OVERVIEW
# ============================================================================
with tab_overview:
    total_orders = filtered[col_client].count()
    total_value = filtered[col_value].sum()
    avg_duration_hrs = filtered["Dispatch Duration (hrs)"].mean()
    total_qty = filtered[col_qty].sum()
    delivered_count = filtered["Is Delivered"].sum()
    delivery_pct = (
        (delivered_count / total_orders * 100) if total_orders else 0
    )
    avg_order_value = total_value / total_orders if total_orders else 0
    unique_clients = filtered[col_client].nunique()

    # Calculate Creation-to-Delivery TAT KPI
    avg_tat_hrs = filtered["Creation_Delivery_TAT"].mean()
    if pd.notna(avg_tat_hrs):
        tat_str = f"{avg_tat_hrs:.1f} hrs"
    else:
        tat_str = "N/A"

    if pd.notna(avg_duration_hrs):
        if avg_duration_hrs < 24:
            duration_str = f"{avg_duration_hrs:.1f} hrs"
        else:
            days = avg_duration_hrs / 24.0
            duration_str = f"{avg_duration_hrs:.1f} hrs ({days:.1f}d)"
    else:
        duration_str = "N/A"

    # Row 1: Primary Order & Delivery KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Dispensed Orders", f"{total_orders:,}")
    c2.metric("Total Order Value", f"₦{total_value:,.0f}")
    c3.metric(
        "Fulfillment Rate",
        f"{delivery_pct:.1f}%",
        f"{int(delivered_count)}/{int(total_orders)} Delivered",
    )
    c4.metric("Avg Creation-Delivery TAT", tat_str)

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 2: Secondary Performance & Volume Metrics
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Avg Dispatch Duration", duration_str)
    c6.metric("Total Volume Shipped", f"{total_qty:,.0f} CTN")
    c7.metric("Avg Order Value", f"₦{avg_order_value:,.0f}")
    c8.metric("Active Health Facilities", f"{unique_clients:,}")

    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### Regional Distribution")
        st.caption("Order volume and value by delivery region")
        region_summary = (
            filtered.groupby(col_region)
            .agg(Orders=(col_client, "count"), Value=(col_value, "sum"))
            .reset_index()
            .sort_values("Orders", ascending=False)
        )

        fig = px.bar(
            region_summary,
            x=col_region,
            y="Orders",
            color=col_region,
            text="Orders",
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Dark2,
        )
        fig.update_layout(
            showlegend=False, height=380, margin=dict(t=20, b=20, l=10, r=10)
        )
        fig = polish_plot(fig, 380)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("### Fulfillment Status")
        st.caption("Current delivery outcome mix")
        status_summary = filtered[col_status].value_counts().reset_index()
        status_summary.columns = ["Status", "Count"]

        fig = px.pie(
            status_summary,
            names="Status",
            values="Count",
            hole=0.5,
            template="plotly_white",
            color_discrete_sequence=[
                "#00A86B",
                "#1E3E62",
                "#E63946",
                "#FFB703",
            ],
        )
        fig.update_layout(height=380, margin=dict(t=20, b=20, l=10, r=10))
        fig = polish_plot(fig, 380)
        st.plotly_chart(fig, use_container_width=True)

    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown("### Weekly Order Value")
        st.caption("Distribution value trend across operating weeks")
        week_summary = (
            filtered.groupby(["Year", "Week", "Week Label"])
            .agg(Value=(col_value, "sum"), Orders=(col_client, "count"))
            .reset_index()
            .sort_values(["Year", "Week"])
        )

        fig = px.line(
            week_summary,
            x="Week Label",
            y="Value",
            markers=True,
            template="plotly_white",
            line_shape="spline",
        )
        fig.update_traces(line_color="#00A86B", line_width=3)
        fig.update_layout(
            height=380, xaxis_title="Week", yaxis_title="Value (₦)"
        )
        fig = polish_plot(fig, 380)
        st.plotly_chart(fig, use_container_width=True)

    with col_d:
        st.markdown("### Weekly Carton Volume")
        st.caption("Physical volume shipped across operating weeks")
        qty_week = (
            filtered.groupby("Week Label")[col_qty].sum().reset_index()
        )

        fig2 = px.area(
            qty_week, x="Week Label", y=col_qty, template="plotly_white"
        )
        fig2.update_traces(
            fillcolor="rgba(0, 168, 107, 0.25)", line_color="#00A86B"
        )
        fig2.update_layout(
            height=380, xaxis_title="Week", yaxis_title="Quantity (Cartons)"
        )
        fig2 = polish_plot(fig2, 380)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Top 10 Health Facilities / Accounts by Value")
    top_clients = (
        filtered.groupby(col_client)
        .agg(Orders=(col_client, "count"), Value=(col_value, "sum"))
        .reset_index()
        .sort_values("Value", ascending=False)
        .head(10)
    )

    fig = px.bar(
        top_clients,
        x="Value",
        y=col_client,
        orientation="h",
        text="Orders",
        template="plotly_white",
        color="Value",
        color_continuous_scale="Tealgrn",
    )
    fig.update_layout(
        height=420,
        yaxis={"categoryorder": "total ascending"},
        coloraxis_showscale=False,
    )
    fig = polish_plot(fig, 420)
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# TAB 2: CAPTAIN PERFORMANCE
# ============================================================================
with tab_captains:
    if col_captain is None:
        st.info(
            "No Delivery Captain/Rider column mapped. Select your rider column in sidebar settings."
        )
    else:
        cap_df = filtered.dropna(subset=[col_captain])
        st.subheader("Rider & Captain Performance Metrics")

        cap_summary = (
            cap_df.groupby(col_captain)
            .agg(
                Total_Orders=(col_client, "count"),
                Total_Value=(col_value, "sum"),
                Total_Qty=(col_qty, "sum"),
                Avg_Duration_Hrs=("Dispatch Duration (hrs)", "mean"),
                Avg_TAT_Hrs=("Creation_Delivery_TAT", "mean"),
                Delivered=("Is Delivered", "sum"),
            )
            .reset_index()
        )
        cap_summary["Delivery Rate %"] = (
            cap_summary["Delivered"] / cap_summary["Total_Orders"] * 100
        ).round(1)
        cap_summary = cap_summary.sort_values("Total_Orders", ascending=False)

        best_captain = (
            cap_summary.iloc[0][col_captain] if not cap_summary.empty else "N/A"
        )
        best_delivery = cap_summary.sort_values(
            "Delivery Rate %", ascending=False
        ).iloc[0]
        fastest = cap_summary.sort_values(
            "Avg_TAT_Hrs", ascending=True
        ).iloc[0]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Active Fleet Captains", f"{cap_summary.shape[0]:,}")
        m2.metric("Highest Dispatch Captain", str(best_captain))
        m3.metric(
            "Top Reliability Score",
            f"{best_delivery[col_captain]}",
            f"{best_delivery['Delivery Rate %']:.1f}%",
        )
        m4.metric(
            "Fastest Creation-Delivery TAT",
            f"{fastest[col_captain]}",
            (
                f"{fastest['Avg_TAT_Hrs']:.1f} hrs"
                if pd.notna(fastest["Avg_TAT_Hrs"])
                else "N/A"
            ),
        )

        st.markdown("### ")
        col_e, col_f = st.columns(2)

        with col_e:
            st.subheader("Total Orders Handled per Captain")
            fig = px.bar(
                cap_summary,
                x=col_captain,
                y="Total_Orders",
                text="Total_Orders",
                color="Total_Orders",
                template="plotly_white",
                color_continuous_scale="Viridis",
            )
            fig.update_layout(
                height=400, coloraxis_showscale=False, xaxis_tickangle=-30
            )
            fig = polish_plot(fig, 400)
            st.plotly_chart(fig, use_container_width=True)

        with col_f:
            st.subheader("Successful Delivery Rate (%)")
            fig = px.bar(
                cap_summary.sort_values("Delivery Rate %"),
                x="Delivery Rate %",
                y=col_captain,
                orientation="h",
                text="Delivery Rate %",
                template="plotly_white",
                color="Delivery Rate %",
                color_continuous_scale="Emrld",
            )
            fig.update_layout(height=400, coloraxis_showscale=False)
            fig = polish_plot(fig, 400)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Comprehensive Captain Scorecard")
        display_cap = cap_summary.rename(
            columns={
                col_captain: "Captain / Rider",
                "Total_Orders": "Total Dispatches",
                "Total_Value": "Order Value",
                "Total_Qty": "Volume (CTN)",
                "Avg_Duration_Hrs": "Avg Dispatch Duration (Hrs)",
                "Avg_TAT_Hrs": "Avg Creation-Delivery TAT (Hrs)",
                "Delivered": "Completed Deliveries",
            }
        )
        scorecard_style = style_scorecard(display_cap).format(
            {
                "Order Value": "₦{:,.0f}",
                "Volume (CTN)": "{:,.0f}",
                "Avg Dispatch Duration (Hrs)": "{:.1f}",
                "Avg Creation-Delivery TAT (Hrs)": "{:.1f}",
                "Delivery Rate %": "{:.1f}%",
            }
        )

        st.dataframe(
            scorecard_style,
            use_container_width=True,
            hide_index=True,
        )

# ============================================================================
# TAB 3: AUDIT & RAW DATA
# ============================================================================
with tab_data:
    st.subheader("Filtered Delivery Logs")

    def highlight_status(row):
        styles = [""] * len(row)
        try:
            idx = list(row.index).index(col_status)
            color = status_color(row[col_status])
            styles[idx] = (
                f"color: {color}; font-weight: 800; "
                f"background-color: {color}18;"
            )
        except ValueError:
            pass
        return styles

    st.dataframe(
        filtered.style.apply(highlight_status, axis=1),
        use_container_width=True,
        height=540,
        hide_index=True,
    )

    st.download_button(
        "⬇️ Download Filtered Audit Report (CSV)",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name=f"DrugStoc_Logistics_Export_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )


# ----------------------------------------------------------------------------
# FOOTER
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div style="
        margin-top:2rem;
        padding:1rem 0;
        border-top:1px solid #D9E2EA;
        text-align:center;
        color:#627D98;
        font-size:.74rem;">
        <b style="color:#0B243A;">DrugStoc Logistics Control Tower</b>
        &nbsp;•&nbsp; Pharmaceutical Supply Chain Analytics
        &nbsp;•&nbsp; Built for Operations
    </div>
    """,
    unsafe_allow_html=True,
)
# ----------------------------------------------------------------------------
# APPEARANCE CONTROL
# ----------------------------------------------------------------------------
if "ds_dark_mode" not in st.session_state:
    st.session_state.ds_dark_mode = False

theme_toggle = st.sidebar.toggle(
    "🌙 Dark mode",
    value=st.session_state.ds_dark_mode,
    help="Switch between the light and dark DrugStoc dashboard themes.",
)
st.session_state.ds_dark_mode = theme_toggle

if theme_toggle:
    st.markdown(
        """
        <style>
            :root {
                --ds-bg: #0B1720;
                --ds-surface: #10232F;
                --ds-surface-2: #142B39;
                --ds-border: #294555;
                --ds-text: #E8F2F7;
                --ds-heading: #EAF6FB;
                --ds-muted: #AFC4CF;
                --ds-input: #10232F;
                --ds-shadow: rgba(0,0,0,.25);
                --ds-header-start: #061E31;
                --ds-header-end: #006C56;
            }

            .stApp {
                background:
                    radial-gradient(circle at 90% 0%, rgba(0,168,120,.11), transparent 24rem),
                    linear-gradient(180deg, #08141C 0%, #0B1720 100%) !important;
                color: #E8F2F7 !important;
            }

            .block-container,
            .stMarkdown,
            .stText,
            p,
            label {
                color: #E8F2F7 !important;
            }

            h1, h2, h3, h4, h5, h6 {
                color: #EAF6FB !important;
            }

            div[data-testid="stMetric"] {
                background: #10232F !important;
                border-color: #294555 !important;
            }

            div[data-testid="stMetric"] *,
            div[data-testid="stMetricValue"] * {
                color: #E8F2F7 !important;
            }

            div[data-testid="stMetricLabel"] *,
            div[data-testid="stMetricLabel"] label,
            div[data-testid="stMetricLabel"] p {
                color: #AFC4CF !important;
            }

            .ds-filter-summary {
                background: rgba(0,168,120,.12) !important;
                border-color: rgba(0,168,120,.28) !important;
                color: #BCEBDD !important;
            }

            .stTabs [data-baseweb="tab-list"] {
                background: #0E202C !important;
                border-color: #294555 !important;
            }

            .stTabs [data-baseweb="tab"] {
                color: #B5C9D4 !important;
            }

            .stTabs [aria-selected="true"] {
                background: #102D3C !important;
                color: #6FE0B7 !important;
            }

            div[data-baseweb="select"] > div,
            div[data-testid="stFileUploaderDropzone"] {
                background: #10232F !important;
                border-color: #355365 !important;
                color: #E8F2F7 !important;
            }

            div[data-baseweb="select"] * {
                color: #E8F2F7 !important;
            }

            .stButton > button,
            .stDownloadButton > button {
                background: #102D3C !important;
                border-color: #355365 !important;
                color: #E8F2F7 !important;
            }

            div[data-testid="stDataFrame"] {
                border-color: #294555 !important;
            }

            [role="listbox"],
            [role="option"] {
                background: #10232F !important;
                color: #E8F2F7 !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

