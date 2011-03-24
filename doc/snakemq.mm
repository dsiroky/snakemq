<map version="0.9.0">
<!-- To view this file, download free mind mapping software FreeMind from http://freemind.sourceforge.net -->
<node CREATED="1297010999219" ID="ID_918844270" MODIFIED="1300789808062" TEXT="snakemq">
<node CREATED="1297011032535" FOLDED="true" ID="ID_1133358496" MODIFIED="1300800173361" POSITION="right" TEXT="queues">
<node CREATED="1297011067899" ID="ID_451965478" MODIFIED="1297011086107" TEXT="receive - simple"/>
<node CREATED="1297011086784" ID="ID_1446171883" MODIFIED="1299534811136" TEXT="send">
<node CREATED="1297011107502" ID="ID_356308449" MODIFIED="1299498854375" TEXT="direct, bound to a named peer (not a link)"/>
<node CREATED="1299499077909" ID="ID_717256879" MODIFIED="1299499130376" TEXT="pairing named peer - connection"/>
<node CREATED="1299499015655" ID="ID_1311715441" MODIFIED="1299499034567" TEXT="exists only if contains non-obsolete (by TTL) items"/>
<node CREATED="1299534812141" FOLDED="true" ID="ID_1997825893" MODIFIED="1299582111745" TEXT="persistency">
<node CREATED="1299535900269" ID="ID_1884185167" MODIFIED="1299576084241" STYLE="fork" TEXT="ttl? easy for graceful process quit, but how about crash?">
<icon BUILTIN="help"/>
<node CREATED="1299576124554" ID="ID_848455887" MODIFIED="1299576138267" TEXT="time of the crash is unknown"/>
<node CREATED="1299576085202" ID="ID_623436916" MODIFIED="1299576086223" TEXT="edge event (conn/disconn) time as a checkpoint - ttls are automatically updated on connect, affordable inaccuracy"/>
<node CREATED="1299576087765" ID="ID_1170027652" MODIFIED="1299582098682" TEXT="store items with absolute ttl">
<icon BUILTIN="button_cancel"/>
</node>
<node CREATED="1299580564732" ID="ID_1627379285" MODIFIED="1299582090914" TEXT="lets presume that process downtime is not relevant">
<icon BUILTIN="button_ok"/>
</node>
</node>
</node>
</node>
</node>
<node CREATED="1297011260095" FOLDED="true" ID="ID_969321100" MODIFIED="1300800167636" POSITION="left" TEXT="reception">
<node CREATED="1297011264976" ID="ID_732551180" MODIFIED="1297011452079" TEXT="msg is for host, enqueue">
<node CREATED="1297011455491" ID="ID_1467587860" MODIFIED="1297011458500" TEXT="#local"/>
<node CREATED="1297011459894" ID="ID_834570018" MODIFIED="1297012292911" TEXT="#pubsub - distribute immediatelly to &quot;direct&quot; queues"/>
</node>
<node CREATED="1297011289917" ID="ID_1290045334" MODIFIED="1297011332316" TEXT="msg is for another, find a &quot;direct&quot; queue"/>
</node>
<node CREATED="1299167304787" FOLDED="true" ID="ID_1629449302" MODIFIED="1300800175480" POSITION="right" TEXT="sending-receiving pipes - on the fly">
<node CREATED="1299167322921" ID="ID_1192951377" MODIFIED="1299499383952" TEXT="streaming, chunked encoding"/>
</node>
<node CREATED="1299497659432" FOLDED="true" ID="ID_1247250275" MODIFIED="1300800170233" POSITION="left" TEXT="TTL">
<node CREATED="1299498007847" ID="ID_1797100669" MODIFIED="1299499049257" TEXT="decreased only by duration of disconnected link"/>
</node>
<node CREATED="1297011101926" FOLDED="true" ID="ID_1043473354" MODIFIED="1299571966861" POSITION="right" TEXT="channels">
<node CREATED="1297011180915" ID="ID_1743834311" MODIFIED="1297011194168" TEXT="only for pub-sub"/>
<node CREATED="1297011171272" ID="ID_224780434" MODIFIED="1297011210583" TEXT="messages flows from those to &quot;direct&quot; queues"/>
<node CREATED="1297012131369" ID="ID_255385174" MODIFIED="1297012161112" TEXT="no need for a queue, distribute it immediatelly to &quot;direct&quot;"/>
<node CREATED="1297012201888" ID="ID_1532254381" MODIFIED="1297012207399" TEXT="# local channel"/>
</node>
<node CREATED="1300789702193" ID="ID_190977860" MODIFIED="1300911173559" POSITION="left" TEXT="rpc">
<node CREATED="1300789724413" ID="ID_354308955" MODIFIED="1300789730228" TEXT="calling timeout"/>
<node CREATED="1300793018481" ID="ID_1028735526" MODIFIED="1300910011973" TEXT="msg prefix - rpc"/>
<node CREATED="1300911174322" ID="ID_503888775" MODIFIED="1300911191809" TEXT="lost connection - wait for reconnect and then re-request again"/>
</node>
<node CREATED="1300789808858" ID="ID_492055641" MODIFIED="1300789859532" POSITION="right" TEXT="receive hooks - must be regexp"/>
</node>
</map>
