# Saga Login

A look at how Saga launches and communicates with Lich, as a potential
effort to explore alternative game proxies that still integrate nicely with
Saga via its Lich integration.

## Launch

Saga 0.10.4 passes the following args to the `ruby` executable capable of
launching `lich.rbw`. Here `LICH_DIRECTORY` is setting in Saga.

```sh
arg[1]: ${LICH_DIRECTORY}/lich.rbw
arg[2]: /var/folders/9_/p6vg5fvn4ylbcwm0j0lgtrmh0000gn/T/saga-${CHARACTER_NAME}-xv9p8wrt.sal
arg[3]: --gtk
arg[4]: --without-frontend
arg[5]: --detachable-client=57295
arg[6]: --saga
```
Here, the second argument is the path to a `.sal` credential file that looks
like

```sh
GAME=STORM
GAMECODE=GS3
GAMEHOST=storm.gs4.game.play.net
GAMEPORT=10024
KEY=abcdefghijklmnopqrstuvwxyz123456
CHARACTER=${CHARACTER_NAME}
```

Presumably any launcher that could read the `.sal` file for credentials and use
it to log into the game would be a valid proxy for Saga.
