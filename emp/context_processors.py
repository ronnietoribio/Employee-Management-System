from emp.models import Settings

def theme_settings(request):
    try:
        settings = Settings.objects.first()
        if not settings:
            settings = Settings.objects.create()
        
        return {
            'theme_primary_color': settings.primary_color,
            'theme_secondary_color': settings.secondary_color,
            'theme_text_color': settings.text_color,
            'theme_header_style': settings.header_style,
            'theme_border_radius': f"{settings.border_radius}px",
            'theme_font_size': {
                'base': '14px' if settings.font_size == 'small' else '16px' if settings.font_size == 'medium' else '18px',
                'heading': '1.5em' if settings.font_size == 'small' else '1.75em' if settings.font_size == 'medium' else '2em',
                'input': '14px' if settings.font_size == 'small' else '16px' if settings.font_size == 'medium' else '18px',
            },
            'company_name': settings.company_name,
        }
    except:
        # Fallback values if settings table doesn't exist yet
        return {
            'theme_primary_color': '#50024d',
            'theme_secondary_color': '#0e6001',
            'theme_text_color': '#000000',
            'theme_header_style': 'solid',
            'theme_border_radius': '8px',
            'theme_font_size': {
                'base': '16px',
                'heading': '1.75em',
                'input': '16px',
            },
            'company_name': 'My Company',
        } 