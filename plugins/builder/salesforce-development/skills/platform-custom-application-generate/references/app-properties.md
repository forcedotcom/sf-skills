# CustomApplication: Purpose, Device Support, User Experience, and Integration Points

## Purpose
- Organize related functionality into focused applications
- Group tabs and components for specific user roles
- Provide tailored user experiences
- Control access to specific features and data
- Use Standard navigation for general business applications or Console navigation for specialized service/support workflows requiring multi-tab workspaces
- Create professional, branded application identity with custom colors and branding
- Override standard actions with custom Lightning pages for enhanced user experience
- Enable profile-specific experiences through profile action overrides

## Device Support

### Desktop Configuration
- **formFactor**: "Large"
- **tabs**: Full list of application tabs

### Phone Configuration
- **formFactor**: "Small"
- **tabs**: Mobile-optimized tab selection

### Tablet Configuration
- **formFactor**: "Medium"
- **tabs**: Tablet-appropriate tab selection

## User Experience Features

### Navigation Behavior
- **Auto Temporary Tabs**: Can be enabled/disabled
- **Personalization**: User customization options
- **Tab Persistence**: Remember user's tab selections

### Accessibility
- **Keyboard Navigation**: Full keyboard support
- **Screen Reader**: Compatible with assistive technologies
- **High Contrast**: Support for high contrast modes

## Integration Points
- **Custom Tabs**: Include custom object and web tabs
- **Standard Tabs**: Include standard Salesforce tabs
- **Lightning Pages**: Integrate with Lightning page layouts
- **Components**: Include custom Lightning components

## General Design Practices
- **Use clear, descriptive application names**
- **Group related functionality logically**
- **Consider different user roles and needs**
- **Test across different device types**
- **Ensure proper permissions and access control**
- **Provide meaningful descriptions for users**
- **Follow consistent naming conventions**
