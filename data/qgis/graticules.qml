<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34.0-Prizren" styleCategories="Symbology|Labeling" labelsEnabled="1">
  <renderer-v2 type="RuleRenderer" symbollevels="0" referencescale="-1" enableorderby="0" forceraster="0">
    <rules key="{8a110001-0000-4000-8000-000000000000}">
      <rule key="{8a110001-0000-4000-8000-000000000001}" label="赤道 / 本初子午线 (0°)" filter="&quot;special&quot; IN ('equator', 'prime')" symbol="0"/>
      <rule key="{8a110001-0000-4000-8000-000000000002}" label="15° 主经纬线" filter="&quot;step&quot; = 15 AND &quot;special&quot; NOT IN ('equator', 'prime')" symbol="1"/>
      <rule key="{8a110001-0000-4000-8000-000000000003}" label="5° 区域经纬线" filter="&quot;step&quot; = 5" scalemindenom="0" scalemaxdenom="45000000" symbol="2"/>
      <rule key="{8a110001-0000-4000-8000-000000000004}" label="1° 精细经纬线" filter="&quot;step&quot; = 1" scalemindenom="0" scalemaxdenom="12000000" symbol="3"/>
    </rules>
    <symbols>
      <symbol type="line" name="0" alpha="0.72" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleLine" enabled="1" locked="0" pass="0">
          <Option type="Map">
            <Option type="QString" name="line_color" value="233,204,133,255"/>
            <Option type="QString" name="line_style" value="solid"/>
            <Option type="QString" name="line_width" value="0.45"/>
            <Option type="QString" name="line_width_unit" value="MM"/>
          </Option>
        </layer>
      </symbol>
      <symbol type="line" name="1" alpha="0.52" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleLine" enabled="1" locked="0" pass="0">
          <Option type="Map">
            <Option type="QString" name="line_color" value="201,162,75,255"/>
            <Option type="QString" name="line_style" value="solid"/>
            <Option type="QString" name="line_width" value="0.32"/>
            <Option type="QString" name="line_width_unit" value="MM"/>
          </Option>
        </layer>
      </symbol>
      <symbol type="line" name="2" alpha="0.44" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleLine" enabled="1" locked="0" pass="0">
          <Option type="Map">
            <Option type="QString" name="line_color" value="127,169,201,255"/>
            <Option type="QString" name="line_style" value="solid"/>
            <Option type="QString" name="line_width" value="0.24"/>
            <Option type="QString" name="line_width_unit" value="MM"/>
          </Option>
        </layer>
      </symbol>
      <symbol type="line" name="3" alpha="0.34" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleLine" enabled="1" locked="0" pass="0">
          <Option type="Map">
            <Option type="QString" name="line_color" value="108,138,166,255"/>
            <Option type="QString" name="line_style" value="dash"/>
            <Option type="QString" name="line_width" value="0.18"/>
            <Option type="QString" name="line_width_unit" value="MM"/>
            <Option type="QString" name="use_custom_dash" value="1"/>
            <Option type="QString" name="customdash" value="1.2;1.2"/>
            <Option type="QString" name="customdash_unit" value="MM"/>
          </Option>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <labeling type="rule-based">
    <rules key="{8a110002-0000-4000-8000-000000000000}">
      <rule key="{8a110002-0000-4000-8000-000000000001}" description="15° 标注" filter="&quot;step&quot; = 15">
        <settings calloutType="simple">
          <text-style fieldName="label" fontFamily="Microsoft YaHei" fontSize="9.5" fontSizeUnit="Point" fontWeight="600" textColor="233,204,133,255" textOpacity="0.92" isExpression="0">
            <text-buffer bufferDraw="1" bufferSize="0.9" bufferSizeUnits="MM" bufferColor="10,14,24,255" bufferOpacity="0.88"/>
          </text-style>
          <placement placement="2" repeatDistance="110" repeatDistanceUnits="MM" dist="1.2" distUnits="MM" priority="7"/>
          <rendering scaleVisibility="0" labelPerPart="0" obstacle="0"/>
        </settings>
      </rule>
      <rule key="{8a110002-0000-4000-8000-000000000002}" description="5° 标注" filter="&quot;step&quot; = 5" scalemindenom="0" scalemaxdenom="45000000">
        <settings calloutType="simple">
          <text-style fieldName="label" fontFamily="Microsoft YaHei" fontSize="8.5" fontSizeUnit="Point" fontWeight="500" textColor="168,205,232,255" textOpacity="0.88" isExpression="0">
            <text-buffer bufferDraw="1" bufferSize="0.8" bufferSizeUnits="MM" bufferColor="10,14,24,255" bufferOpacity="0.86"/>
          </text-style>
          <placement placement="2" repeatDistance="95" repeatDistanceUnits="MM" dist="1.0" distUnits="MM" priority="5"/>
          <rendering scaleVisibility="1" scaleMin="0" scaleMax="45000000" labelPerPart="0" obstacle="0"/>
        </settings>
      </rule>
      <rule key="{8a110002-0000-4000-8000-000000000003}" description="1° 标注" filter="&quot;step&quot; = 1" scalemindenom="0" scalemaxdenom="10000000">
        <settings calloutType="simple">
          <text-style fieldName="label" fontFamily="Microsoft YaHei" fontSize="8" fontSizeUnit="Point" fontWeight="400" textColor="148,180,208,255" textOpacity="0.82" isExpression="0">
            <text-buffer bufferDraw="1" bufferSize="0.7" bufferSizeUnits="MM" bufferColor="10,14,24,255" bufferOpacity="0.82"/>
          </text-style>
          <placement placement="2" repeatDistance="85" repeatDistanceUnits="MM" dist="0.8" distUnits="MM" priority="3"/>
          <rendering scaleVisibility="1" scaleMin="0" scaleMax="10000000" labelPerPart="0" obstacle="0"/>
        </settings>
      </rule>
    </rules>
  </labeling>
</qgis>
