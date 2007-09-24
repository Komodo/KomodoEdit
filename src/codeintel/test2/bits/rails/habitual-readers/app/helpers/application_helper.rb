# Methods added to this helper will be available to all templates in the application.
module ApplicationHelper
  
  def column_headings(column_names, show_actions=FALSE)
		column_names.insert(0,"Action") if show_actions
		content_tag("thead", 
		  content_tag("tr",
        column_names.collect do |column_name| 
          content_tag("th", column_name ) 
        end
      )
    )
  end
  
  def link_to_controller(this_controller, options = {})
    element_class = (this_controller == params[:controller] ? 'active' : 'normal')
    link_to(options[:with_label]||this_controller.titleize, {:controller => this_controller}, {:class => element_class})
  end
  
  def next_previous_links_for(paginator)
    (link_to_if paginator.current.previous, "Previous Page", {:page => paginator.current.previous}) +
    " " +
    (link_to_if paginator.current.next, "Next Page", {:page => paginator.current.next})     
  end
  
  def field_tag_with_label(field, html, label, help)
    @template.content_tag("label", label||field.to_s.humanize, :for => field.to_s) +
      tag("br") +
      html +
      tag("br") +
      (help ? @template.content_tag("label", help, :class => "example") : "")
  end    
    
  class HabitualFormBuilder < ActionView::Helpers::FormBuilder
    (field_helpers - %w(check_box radion_button hidden_field)).each do |selector|
      src = <<-END_SRC
       def #{selector}(field, options = {})
         help = options.delete(:help)
         label = options.delete(:label)
         @template.field_tag_with_label(field, super(field, options), label, help)
       end
      END_SRC
      class_eval src, __FILE__, __LINE__
    end
  end
  
  def my_form_for(name, object = nil, options = nil, &proc)
    concat("<div class='habitual-form'>", proc.binding)
    form_for(name, 
             object,
             (options||{}).merge(:builder => HabitualFormBuilder),
             &proc)
    concat("</div>", proc.binding)
  end
  
  # helpers to determine paths for forms that are used for both creates and adds
  def route_for(resource, *args)
    if args.last.new_record?
      args.delete(args.last)
      send("#{resource}_path", *args) 
    else 
      send("#{resource.singularize}_path", *args)  
    end
  end
  
end
