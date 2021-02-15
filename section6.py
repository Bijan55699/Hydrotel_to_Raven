def addsubwatershed(path,subwatershed):

    print ('adding subwatershed ID to the attribute table')
    import arcpy, os, re
    # from arcpy.sa import *
    from arcpy import env
    arcpy.env.workspace = path

    HRU6 = os.path.join(path, "HRU6")
    HRU_final = os.path.join(path, "HRU_final")

    fms = arcpy.FieldMappings()
    # loading all field objects from joinFC into the <FieldMappings object>
    fms.addTable(subwatershed)

    fields_sequence = ['Troncon_id']
    # remove fieldmaps for those fields that are not needed in the output joined fc
    fields_to_delete = [f.name for f in fms.fields if f.name not in fields_sequence]
    for field in fields_to_delete:
        fms.removeFieldMap(fms.findFieldMapIndex(field))

    # currently field mappings from counties have just two fields we have left
    # [f.name for f in fms.fields] [u'NAME', u'CNTY_FIPS']

    # now need to create a new fms and loat all fields from cities fc
    # compiling output fms - all fields from cities
    fms_out = arcpy.FieldMappings()
    fms_out.addTable(HRU6)

    # we need to add Troncon_ID to fieldmapping
    for field in fields_sequence:
        mapping_index = fms.findFieldMapIndex(field)
        field_map = fms.fieldMappings[mapping_index]
        fms_out.addFieldMap(field_map)

    # [f.name for f in fms_out.fields] [all HRU5 fields ] + [Troncon_id]

    arcpy.SpatialJoin_analysis(target_features=HRU6, join_features=subwatershed,
                               out_feature_class=HRU_final,
                               join_operation='JOIN_ONE_TO_ONE', join_type='KEEP_ALL',
                               field_mapping=fms_out, match_option='WITHIN',
                               search_radius=None, distance_field_name=None)

    arcpy.DeleteField_management(HRU_final, ["ident", "Join_Count", "TARGET_FID"])

    print('done!')
