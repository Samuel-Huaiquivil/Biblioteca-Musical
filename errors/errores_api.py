def process_pipeline(raw_items):
    for item in raw_items:
        try:
            # 1. Validación Externa
            external_data = ExternalSchema.model_validate(item)
            
            # 2. Transformación
            internal_data = adapter.transform(external_data)
            
            # 3. Persistencia (Upsert)
            db.upsert(internal_data)
            
        except ValidationError as ve:
            # Error de formato (dato corrupto de origen)
            log_error_to_dlq(item, error_type="VALIDATION_FAILED", detail=ve.errors())
        
        except DatabaseError as de:
            # Error de base de datos
            log_error_to_dlq(item, error_type="DB_WRITE_FAILED", detail=str(de))
            
        except Exception as e:
            # Error inesperado
            log_error_to_dlq(item, error_type="UNKNOWN", detail=str(e))